"""Scheduled timing, holiday selection and duplicate-delivery guards; no network sends."""
import datetime as dt
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import weekly
import delivery


class PublicationTests(unittest.TestCase):
    def test_supported_holiday_wednesdays_by_year(self):
        for date,theme in [('2026-10-28','halloween'),('2026-11-25','thanksgiving'),
                           ('2026-12-23','christmas'),('2024-12-25','christmas'),
                           ('2027-10-27','halloween'),('2027-11-24','thanksgiving'),
                           ('2027-12-22','christmas'),('2026-11-04','regular'),
                           ('2026-07-01','regular'),('2026-11-26','regular')]:
            with self.subTest(date=date):
                self.assertEqual(weekly.theme_for(dt.date.fromisoformat(date)),theme)

    def test_early_capture_is_actual_time_and_final_waits(self):
        cutoff=weekly.instant('2026-11-04T13:00:00Z')
        early=weekly.instant('2026-11-04T12:00:00Z')
        self.assertEqual(weekly.reporting_end(cutoff,True,now=early),early)
        with self.assertRaises(ValueError):weekly.reporting_end(cutoff,False,now=early)
        self.assertEqual(weekly.reporting_end(cutoff,False,now=cutoff),cutoff)
        with tempfile.TemporaryDirectory() as name:
            capture=Path(name)
            weekly.save(capture/'capture.json',{'provisional':True,'scheduled_cutoff':weekly.iso(cutoff),
                                               'coverage_end_exclusive':weekly.iso(early)})
            self.assertEqual(weekly.reporting_end(cutoff,True,capture,now=cutoff),early)

    def test_provisional_draft_cannot_be_published_or_recorded(self):
        with tempfile.TemporaryDirectory() as name:
            folder=Path(name)/'draft';folder.mkdir()
            weekly.save(folder/'draft.json',{'season':'2026','week':7,'cutoff':'2026-10-28T11:00:00Z','provisional':True})
            with self.assertRaisesRegex(ValueError,'Provisional'):weekly.record_history(folder,weekly.load(ROOT/'config.json'))
            with self.assertRaisesRegex(ValueError,'Provisional'):
                delivery.update(Path(name)/'state.json','2026',7,'published',
                    url='https://aj-flynn.github.io/Sleeper/2026-week7.html',draft=folder,scheduled=True)

    def test_old_week7_is_never_reannounced(self):
        with tempfile.TemporaryDirectory() as name:
            state=Path(name)/'state.json';shutil.copyfile(ROOT/'data/publication-state.json',state)
            self.assertEqual(delivery.update(state,'2026',7,'begin-chat')['action'],'skip')

    def test_auto_render_uses_holiday_and_refuses_placeholder_schedule(self):
        with tempfile.TemporaryDirectory() as name:
            folder=Path(name)/'draft'
            start,end=weekly.window('2026-10-28T12:00:00Z')
            weekly.prepare(ROOT/'data/2026/week7-capture',folder,weekly.load(ROOT/'config.json'),start,end,weekly.load(ROOT/'elo/2026.json'))
            shutil.copyfile(ROOT/'themes/halloween/redesign/week7.json',folder/'issue.json')
            weekly.render_issue(folder)
            self.assertEqual(weekly.load(folder/'draft.json')['theme'],'halloween')
            self.assertNotIn('<p class="bench-note">',(folder/'issue.html').read_text(encoding='utf-8'))
            issue=weekly.load(folder/'issue.json');issue['preview']['is_sample']=True;weekly.save(folder/'issue.json',issue)
            with self.assertRaisesRegex(ValueError,'placeholders'):weekly.render_issue(folder)

    def test_new_scheduled_issue_can_send_once_and_correction_is_silent(self):
        with tempfile.TemporaryDirectory() as name:
            path=Path(name);draft=path/'draft';draft.mkdir()
            weekly.save(draft/'draft.json',{'season':'2026','week':7,'cutoff':'2026-10-28T12:00:00Z','provisional':False})
            url='https://aj-flynn.github.io/Sleeper/2026-week7.html'
            delivery.update(path/'state.json','2026',7,'published',url=url,draft=draft,scheduled=True)
            self.assertEqual(delivery.update(path/'state.json','2026',7,'begin-chat')['chat']['status'],'sending')
            with self.assertRaisesRegex(ValueError,'uncertain'):delivery.update(path/'state.json','2026',7,'begin-chat')
            delivery.update(path/'state.json','2026',7,'sent',receipt='Synthetic visible test receipt')
            delivery.update(path/'state.json','2026',7,'published',url=url,draft=draft)
            self.assertEqual(delivery.update(path/'state.json','2026',7,'begin-chat')['action'],'skip')

    def test_unknown_send_blocks_retry_and_unannounced_correction_is_not_scheduled(self):
        with tempfile.TemporaryDirectory() as name:
            path=Path(name);draft=path/'draft';draft.mkdir()
            weekly.save(draft/'draft.json',{'season':'2026','week':7,'cutoff':'2026-10-28T12:00:00Z'})
            url='https://aj-flynn.github.io/Sleeper/2026-week7.html'
            delivery.update(path/'correction.json','2026',7,'published',url=url,draft=draft)
            self.assertEqual(delivery.update(path/'correction.json','2026',7,'begin-chat')['action'],'skip')
            delivery.update(path/'state.json','2026',7,'published',url=url,draft=draft,scheduled=True)
            delivery.update(path/'state.json','2026',7,'begin-chat')
            delivery.update(path/'state.json','2026',7,'unknown',receipt='Synthetic uncertain test outcome')
            with self.assertRaisesRegex(ValueError,'uncertain'):delivery.update(path/'state.json','2026',7,'begin-chat')


if __name__=='__main__':unittest.main()
