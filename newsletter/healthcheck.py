#!/usr/bin/env python3
"""Read-only dependency checks; optional live league/MCP probes, no data promotion."""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import sys
import urllib.request
import weekly


def probe(url, body=None):
    result,_=weekly.request(url,body,{"Content-Type":"application/json","Accept":"application/json, text/event-stream"},timeout=10)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live',action='store_true')
    parser.add_argument('--config',type=Path,default=weekly.ROOT/'config.json')
    parser.add_argument('--mcp-url',default=os.environ.get('NFL_MCP_URL','http://127.0.0.1:9000/mcp/'))
    args=parser.parse_args()
    report={'python':sys.version.split()[0],'timezone':str(weekly.eastern_zone()),
            'offline_fixture_sources':len(weekly.read_sources(weekly.ROOT/'data/2026/week7-capture'))}
    try:report['playwright']=importlib.metadata.version('playwright')
    except importlib.metadata.PackageNotFoundError:report['playwright']='unavailable; browser QA requires installation'
    report['edge_installed']=Path(r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe').exists()
    if args.live:
        config=weekly.load(args.config)
        try:
            league=probe(config['sleeper_api']+'/league/'+config['league_id'])
            report['sleeper']={'reachable':True,'season':league['season'],'teams':league['total_rosters'],
                'matches_config':str(league['season'])==str(config['season']) and league['total_rosters']==config['teams']}
        except Exception as exc:report['sleeper']={'reachable':False,'error':str(exc)}
        try:
            result=probe(args.mcp_url,{'jsonrpc':'2.0','id':1,'method':'initialize',
                'params':{'protocolVersion':'2024-11-05','capabilities':{},'clientInfo':{'name':'newsletter-health','version':'1'}}})
            report['mcp']={'reachable':'result' in result,'server':result.get('result',{}).get('serverInfo'),
                           'coverage':'Feed contents not checked; empty news/injury caches remain possible'}
        except Exception as exc:report['mcp']={'reachable':False,'error':str(exc),'required_for_data_replay':False}
    print(json.dumps(report,indent=2))
    return 0


if __name__=='__main__':sys.exit(main())
