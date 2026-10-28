"""Offline acceptance tests: python -m unittest discover -s newsletter/tests -p test_weekly.py -v"""
import copy
import datetime as dt
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import elo
import weekly


class WeeklyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.capture=ROOT/'data/2026/week7-capture'
        cls.config=weekly.load(ROOT/'config.json')
        cls.baseline=weekly.load(ROOT/'elo/2026.json')
        cls.start,cls.end=weekly.window('2026-10-28T12:00:00Z')

    def test_dst_and_delayed_run(self):
        start,end=weekly.window('2026-11-04T13:00:00Z')
        self.assertEqual((end-start).total_seconds()/3600,169)
        self.assertEqual(weekly.iso(start),'2026-10-28T12:00:00Z')
        start,end=weekly.window('2027-03-17T12:00:00Z')
        self.assertEqual((end-start).total_seconds()/3600,167)
        self.assertEqual(weekly.window(now=weekly.instant('2026-11-05T18:00:00Z'))[1],weekly.instant('2026-11-04T13:00:00Z'))
        with self.assertRaises(ValueError):weekly.window('2026-11-04T12:00:00Z')

    def test_elo_formula_ties_and_no_margin(self):
        pair=[{'roster_id':1,'matchup_id':1,'points':10},{'roster_id':2,'matchup_id':1,'points':9}]
        result,_=elo.apply_week(pair,{1:1000,2:1000})
        self.assertEqual(result,{1:1016,2:984})
        pair[0]['points']=1000
        self.assertEqual(elo.apply_week(pair,{1:1000,2:1000})[0],result)
        pair[1]['points']=1000
        self.assertEqual(elo.apply_week(pair,{1:1000,2:1000})[0],{1:1000,2:1000})

    def test_tie_jump_list_reports_neither_side_as_a_loss(self):
        import build
        issue=weekly.load(ROOT/'examples/2026-week7-regular/issue.json')
        issue['recaps'][0]['l_score']=issue['recaps'][0]['w_score']
        rendered=build.render(build.derive(issue))
        self.assertEqual(rendered.count('Tied, '),2)
        self.assertEqual(rendered.count('Won, '),5)
        self.assertEqual(rendered.count('Lost, '),5)

    def test_postponed_and_future_games(self):
        board=weekly.load(self.capture/'raw/espn_scoreboard_w7.json')
        self.assertEqual(weekly.latest_week({7:board},self.end),7)
        late=copy.deepcopy(board);late['events'][0]['competitions'][0]['status']['type']['completed']=False
        self.assertEqual(weekly.latest_week({6:board,7:late},self.end),6)
        late['events'][0]['date']='2026-11-01T12:00Z'
        self.assertFalse(weekly.board_done(late,self.end))

    def test_scores_and_zero_valid(self):
        rows=weekly.load(self.capture/'raw/sleeper_matchups_w7.json')
        self.assertEqual(len(weekly.games_and_totals(rows,12)),6)
        rows[0]['points']+=1
        with self.assertRaises(ValueError):weekly.games_and_totals(rows,12)
        rows[0].update(points=0,starters_points=[0]*len(rows[0]['starters']),players_points={p:0 for p in rows[0]['starters']})
        weekly.games_and_totals(rows,12)
        rows.pop()
        with self.assertRaises(ValueError):weekly.games_and_totals(rows,12)

    def test_fixture_ledgers_and_idempotence(self):
        sources=weekly.read_sources(self.capture)
        candidate=weekly.history(self.capture/'raw',7,self.config,self.baseline,self.end,sources)
        self.assertEqual(candidate['elo'],self.baseline)
        self.assertEqual(sum(row['elo'] for row in candidate['elo']['weeks']['7'].values()),12000)
        self.assertTrue(all(row['reconciled'] for row in candidate['faab'].values()))
        expected=weekly.load(self.capture/'data-audit.json')['faab']
        for rid,row in expected.items():
            self.assertEqual(candidate['faab'][rid]['remaining'],row['remaining'])
        self.assertEqual(sum(row['w'] for row in candidate['weeks']['7']['standings']),42)
        with tempfile.TemporaryDirectory() as name:
            out=Path(name)/'draft'
            with weekly.run_lock(out):weekly.prepare(self.capture,out,self.config,self.start,self.end,self.baseline)
            before={p.name:p.read_bytes() for p in out.iterdir()}
            weekly.prepare(self.capture,out,self.config,self.start,self.end,self.baseline)
            self.assertEqual(before,{p.name:p.read_bytes() for p in out.iterdir()})
            period=weekly.load(out/'period-transactions.json')
            self.assertEqual(len(period['completed']),21)
            self.assertEqual(len(period['failed_bids']),3)
            self.assertTrue(any(not row.get('adds') and row.get('drops') for row in period['completed']))
            self.assertEqual(weekly.load(out/'brief.json')['injury_status_at_fetch'],[])

    def test_transaction_boundaries_and_dedup(self):
        with tempfile.TemporaryDirectory() as name:
            p=Path(name);low=int(self.start.timestamp()*1000);high=int(self.end.timestamp()*1000)
            rows=[{'transaction_id':str(i),'status_updated':time} for i,time in enumerate([low-1,low,high-1,high])]
            weekly.save(p/'sleeper_transactions_leg7.json',rows)
            weekly.save(p/'sleeper_transactions_leg8.json',rows)
            before,all_rows=weekly.transaction_ledger(p,self.end)
            self.assertEqual(len(all_rows),4)
            self.assertEqual([r['transaction_id'] for r in before if r['status_updated']>=low],['1','2'])

    def test_late_final_status_requires_pre_cutoff_recap(self):
        with tempfile.TemporaryDirectory() as name:
            capture=Path(name)/'capture';shutil.copytree(self.capture,capture)
            source=next(s for s in weekly.load(capture/'sources.json')['sources'] if s['file'].startswith('espn_summary_'))
            path=capture/'raw'/source['file'];data=weekly.load(path)
            data['article']['published']='2026-10-29T12:00:00Z';weekly.save(path,data)
            with self.assertRaisesRegex(ValueError,'completion uncertain'):
                weekly.prepare(capture,Path(name)/'draft',self.config,self.start,self.end,self.baseline)

    def test_lock_and_partial_write_recovery(self):
        with tempfile.TemporaryDirectory() as name:
            out=Path(name)/'draft'
            with weekly.run_lock(out):
                with self.assertRaises(ValueError):
                    with weekly.run_lock(out):pass
            real_save=weekly.save
            def interrupt_save(path,data):
                if Path(path).name=='draft.json':raise RuntimeError('injected crash after data writes')
                return real_save(path,data)
            with patch.object(weekly,'save',side_effect=interrupt_save):
                with self.assertRaises(RuntimeError):weekly.prepare(self.capture,out,self.config,self.start,self.end,self.baseline)
            self.assertFalse(out.exists())
            self.assertEqual(list(Path(name).iterdir()),[])
            out.mkdir();(out/'brief.json').write_text('{}')
            with self.assertRaises(ValueError):weekly.prepare(self.capture,out,self.config,self.start,self.end,self.baseline)

    def test_corrections_block_and_replay_later_weeks(self):
        with tempfile.TemporaryDirectory() as name:
            raw=Path(name)/'raw';shutil.copytree(self.capture/'raw',raw)
            rows=weekly.load(raw/'sleeper_matchups_w1.json')
            pair=next(pair for pair in weekly.games_and_totals(rows,12).values())
            a,b=pair;a['points'],b['points']=b['points'],a['points']
            for row in pair:
                row['starters_points']=[row['points']]+[0]*(len(row['starters'])-1)
                row['players_points']={pid:point for pid,point in zip(row['starters'],row['starters_points'])}
            weekly.save(raw/'sleeper_matchups_w1.json',rows)
            sources=weekly.read_sources(self.capture)
            with self.assertRaisesRegex(ValueError,'correction'):weekly.history(raw,7,self.config,self.baseline,self.end,sources)
            zero=copy.deepcopy(self.baseline);zero['weeks']={'0':zero['weeks']['0']}
            replay=weekly.history(raw,7,self.config,zero,self.end,sources)
            self.assertNotEqual(replay['elo']['weeks']['7'],self.baseline['weeks']['7'])
            self.assertEqual(len(replay['elo']['weeks']),8)

    def test_rules_rollover_and_renames(self):
        sources=weekly.read_sources(self.capture)
        config={**self.config,'season':'2027'}
        with self.assertRaises(ValueError):weekly.history(self.capture/'raw',7,config,self.baseline,self.end,sources)
        with tempfile.TemporaryDirectory() as name:
            raw=Path(name)/'raw';shutil.copytree(self.capture/'raw',raw)
            users=weekly.load(raw/'sleeper_users.json');users[0]['metadata']['team_name']='Renamed team';weekly.save(raw/'sleeper_users.json',users)
            candidate=weekly.history(raw,7,self.config,self.baseline,self.end,sources)
            self.assertEqual(candidate['elo'],self.baseline)
            self.assertIn('Renamed team',[row['team'] for row in candidate['team_names_observed']])
            league=weekly.load(raw/'sleeper_league.json');league['settings']['league_average_match']=1;weekly.save(raw/'sleeper_league.json',league)
            with self.assertRaisesRegex(ValueError,'median'):weekly.history(raw,7,self.config,self.baseline,self.end,sources)
            league['settings']['league_average_match']=0;league['settings']['playoff_week_start']=7;weekly.save(raw/'sleeper_league.json',league)
            with self.assertRaisesRegex(ValueError,'Playoffs'):weekly.history(raw,7,self.config,self.baseline,self.end,sources)

    def test_tampered_capture_refused(self):
        with tempfile.TemporaryDirectory() as name:
            capture=Path(name)/'capture';shutil.copytree(self.capture,capture)
            (capture/'raw/sleeper_rosters.json').write_text('[]')
            with self.assertRaises(ValueError):weekly.prepare(capture,Path(name)/'draft',self.config,self.start,self.end,self.baseline)

    def test_capture_sources_track_final_schedule_representation(self):
        def fake_request(url,body=None,headers=None,**kwargs):
            raw=self.capture/'raw'
            if '/scoreboard?' in url:
                week=int(url.rsplit('week=',1)[1]);board=weekly.load(raw/'espn_scoreboard_w7.json')
                if week==8:board['events'][0]['competitions'][0]['status']['type']['completed']=False
                return board,{}
            if '/summary?' in url:name='espn_summary_'+url.rsplit('=',1)[1]+'.json'
            elif '/matchups/' in url:name='sleeper_matchups_w'+url.rsplit('/',1)[1]+'.json'
            elif '/transactions/' in url:name='sleeper_transactions_leg'+url.rsplit('/',1)[1]+'.json'
            elif '/players/nfl' in url:name='sleeper_players_rostered.json'
            elif '/stats/nfl/' in url:name='sleeper_stats_w7.json'
            elif url.endswith('/rosters'):name='sleeper_rosters.json'
            elif url.endswith('/users'):name='sleeper_users.json'
            else:name='sleeper_league.json'
            return weekly.load(raw/name),{}
        with tempfile.TemporaryDirectory() as name,patch.object(weekly,'request',side_effect=fake_request):
            capture=Path(name)/'capture'
            self.assertEqual(weekly.collect(capture,self.config,self.start,self.end,''),7)
            sources=weekly.read_sources(capture)
            self.assertEqual(len(sources),len({s['file'] for s in sources}))
            future=weekly.load(capture/'raw/espn_scoreboard_w8.json')
            self.assertNotIn('score',future['events'][0]['competitions'][0]['competitors'][0])

    def test_faab_zero_bid_failed_bid_transfer_and_adjustment(self):
        with tempfile.TemporaryDirectory() as name:
            raw=Path(name)/'raw';shutil.copytree(self.capture/'raw',raw)
            when=int(self.start.timestamp()*1000)+1
            moves=[{'transaction_id':'zero','status_updated':when,'status':'complete','type':'waiver',
                    'adds':{'test':1},'settings':{'waiver_bid':0}},
                   {'transaction_id':'failed','status_updated':when,'status':'failed','type':'waiver',
                    'adds':{'test':1},'settings':{'waiver_bid':199}},
                   {'transaction_id':'transfer','status_updated':when,'status':'complete','type':'trade',
                    'waiver_budget':[{'sender':1,'receiver':2,'amount':10}]}]
            weekly.save(raw/'sleeper_transactions_leg99.json',moves)
            config={**self.config,'faab_adjustments':[{'roster_id':1,'amount':5,'effective_at':weekly.iso(self.start),
                                                     'reason':'test commissioner grant','evidence':'synthetic test'}]}
            candidate=weekly.history(raw,7,config,self.baseline,self.end,weekly.read_sources(self.capture))
            self.assertEqual(candidate['faab']['1']['spent'],50)
            self.assertEqual(candidate['faab']['1']['remaining'],145)
            self.assertEqual(candidate['faab']['2']['remaining'],192)

    def test_render_current_copy_without_approval_paperwork(self):
        with tempfile.TemporaryDirectory() as name:
            folder=Path(name)/'draft'
            weekly.prepare(self.capture,folder,self.config,self.start,self.end,self.baseline)
            shutil.copyfile(ROOT/'examples/2026-week7-regular/issue.json',folder/'issue.json')
            self.assertEqual(weekly.render_issue(folder,'regular')['state'],'draft_ready')
            self.assertNotIn('<p class="bench-note">',(folder/'issue.html').read_text(encoding='utf-8'))
            self.assertNotIn('season-margins',(folder/'issue.html').read_text(encoding='utf-8'))
            self.assertNotIn('approval',weekly.load(folder/'draft.json'))
            brief=weekly.load(folder/'brief.json');brief['fantasy_matchups'][0]['winner']['points']+=1;weekly.save(folder/'brief.json',brief)
            with self.assertRaises(ValueError):weekly.render_issue(folder,'regular')

    def test_optional_holiday_comparisons(self):
        for theme in ['thanksgiving','christmas']:
            with self.subTest(theme=theme),tempfile.TemporaryDirectory() as name:
                folder=Path(name)/'draft'
                weekly.prepare(self.capture,folder,self.config,self.start,self.end,self.baseline)
                shutil.copyfile(ROOT/'themes'/theme/'week7.json',folder/'issue.json')
                weekly.render_issue(folder,theme,trial=True)
                text=(folder/'issue.html').read_text(encoding='utf-8')
                self.assertEqual(text.rstrip(),(ROOT/'themes'/theme/'week7-preview.html').read_text(encoding='utf-8').rstrip())
                self.assertNotIn('awaits AJ',text)
                self.assertIn('season-margins',text)
                self.assertTrue(weekly.load(folder/'draft.json')['trial'])

    def test_recording_does_not_duplicate_weekly_data(self):
        with tempfile.TemporaryDirectory() as name:
            folder=Path(name)/'draft'
            weekly.prepare(self.capture,folder,self.config,self.start,self.end,self.baseline)
            with patch.object(weekly,'ROOT',Path(name)/'repo'):
                weekly.record_history(folder,self.config)
                first=weekly.load(Path(name)/'repo/data/2026/history.json')
                weekly.record_history(folder,self.config)
                self.assertEqual(first,weekly.load(Path(name)/'repo/data/2026/history.json'))
                self.assertEqual(len(first['team_names_observed']),12)


if __name__=='__main__':unittest.main()
