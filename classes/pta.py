import json
import datetime
import requests
from html import escape
from functools import reduce

from requests.auth import HTTPBasicAuth

from utils.XML import XML_dump
from utils.utils import dtime2timestamp, ctime2timestamp, make_ordinal_zh, randomstr

class PTA_school:

    def __init__(self, config):
        self.config = config
        self.award_list = ['"team id","tean name","team group","team affiliation","award","team members"']
        self.raw_judgement_types = []
        self.raw_problems = []
        self.raw_teams = []
        self.raw_persons = []
        self.raw_groups = []
        self.raw_organizations = []
        self.raw_submissions = []
        self.raw_judgements = []
        self.raw_languages = []
        self.load_data()
        self.prep_data()

    def API(self, method):
        req_url = self.config['url'] + method
        print ("[   ] GET %s" % req_url, end='\r')
        res = requests.get(req_url, auth=HTTPBasicAuth(self.config['username'], self.config['password']), verify=False)
        print ("[%d] GET %s" % (res.status_code, req_url))
        with open("eventfeed.json", "w") as f:
            f.write(res.text)
        return [json.loads(i) for i in res.text.split('\n') if i != ""]

    def load_data(self):
        self.load_event_feed()
        self.load_groups()
        self.load_languages()
        self.load_organizations()
        self.load_teams()
        self.load_submissions()
        self.load_judgements()
        self.load_judgement_types()
        self.load_problems()
        self.load_scoreboard()

    def load_event_feed(self):
        tz = datetime.timezone(datetime.timedelta(hours=8))
        if self.config["file"] != "":
            with open(self.config['file'], "r") as f:
                res = f.read()
            tmp = [json.loads(i) for i in res.split('\n') if i != ""]
        else:
            tmp = self.API("event-feed")
        for info in tmp:
            info_type = info["type"]
            info_data = info["data"]
            if info_type == "state":
                self.state_info = info_data
                for key in ['end_of_updates', 'finalized']:
                # for key in ['thawed', 'finalized', 'end_of_updates']:
                    if self.state_info.get(key, None) == None:
                        self.state_info[key] = datetime.datetime.now(tz).isoformat(timespec='seconds')
            elif info_type == "contests":
                self.contest_info = info_data
            elif info_type == "judgement-types":
                self.raw_judgement_types.append(info_data)
            elif info_type == "languages":
                self.raw_languages.append(info_data)
            elif info_type == "problems":
                self.raw_problems.append(info_data)
            elif info_type == "teams":
                self.raw_teams.append(info_data)
            elif info_type == "groups":
                self.raw_groups.append(info_data)
            elif info_type == "organizations":
                self.raw_organizations.append(info_data)
            elif info_type == "persons":
                self.raw_persons.append(info_data)
            elif info_type == "submissions":
                self.raw_submissions.append(info_data)
            elif info_type == "judgements":
                self.raw_judgements.append(info_data)
            else:
                raise KeyError(f"Unknown type {info_type}")

    def load_groups(self):
        groups = self.raw_groups
        # func = lambda group : not group['hidden']
        # groups = list(filter(func, groups))
        self.groups = {group['id'] : group for group in groups}

    def load_languages(self):
        self.languages = self.raw_languages

    def load_organizations(self):
        organizations = self.raw_organizations
        self.organizations = {organization['id']: organization for organization in organizations}

    def load_teams(self):
        teams = self.raw_teams
        group_ids = [group['id'] for group in self.groups.values()]
        same = lambda x, y: list(set(x) & set(y))
        func = lambda team: len(same(team['group_ids'], group_ids))
        # self.teams = list(filter(func, teams))
        self.teams = teams
        self.team_dict = {team['id']: team for team in self.teams}
        for person in self.raw_persons:
            if "members" not in self.team_dict[person["team_id"]]:
                self.team_dict[person["team_id"]]["members"] = []
            self.team_dict[person["team_id"]]["members"].append(person["name"])
        for key in self.team_dict.keys():
            self.team_dict[key]["members"] = '、'.join(self.team_dict[key]["members"])
        self.teams = [value for _, value in self.team_dict.items()]

    def load_submissions(self):
        submissions = self.raw_submissions
        team_ids = [team['id'] for team in self.teams]
        func = lambda submission: submission['team_id'] in team_ids
        self.submissions = list(filter(func, submissions))

    def load_judgements(self):
        judgements = self.raw_judgements
        submission_ids = [submission['id'] for submission in self.submissions]
        func = lambda judgement: judgement['submission_id'] in submission_ids
        self.judgements = list(filter(func, judgements))

    def load_judgement_types(self):
        self.judgement_types = self.raw_judgement_types

    def load_problems(self):
        self.problems = self.raw_problems

    def load_scoreboard(self):
        self.scoreboard = {"rows": []}

    def prep_data(self):
        self.submission_judgement_type()
        self.scoreboard_rank()

    def submission_judgement_type(self):
        id2idx = { submission['id']: idx for idx, submission in enumerate(self.submissions) }
        judgement_types = { judgement_type['id']: judgement_type for judgement_type in self.judgement_types }
        for judgement in self.judgements:
            idx = id2idx[judgement['submission_id']]
            self.submissions[idx]['judgement_type'] = judgement_types[judgement['judgement_type_id']]
        for submission in self.submissions:
            if "judgement_type" not in submission:
                # not in => internel error, but pta ignore
                print(f"Warn submission_id:{submission['id']} {submission['problem_id']} has no judgement, considering WA")
                submission["judgement_type"] = judgement_types["WA"]

    def scoreboard_rank(self):
        for team in self.teams:
            team_id = team["id"]
            num_solved, total_time = 0, 0
            team_submit_func = lambda submission: submission['team_id'] == team_id 
            team_submissions = list(filter(team_submit_func, self.submissions))
            max_submission_id, problems = 0, set()
            penalty = {problem["id"]: 0 for problem in self.problems}
            for submission in team_submissions:
                if submission['problem_id'] in problems:
                    continue
                if submission["judgement_type"]['solved']:
                    problems.add(submission['problem_id'])
                    num_solved += 1
                    hour, minute, second = map(int, submission['contest_time'].split(":"))
                    # total_time += (hour * 60 + minute) * 60 + second + penalty[submission["problem_id"]]
                    total_time += (hour * 60 + minute) * 60 + penalty[submission["problem_id"]] # no seconds
                    max_submission_id = max(max_submission_id, int(submission['id']))
                elif submission["judgement_type"]['penalty']:
                    penalty[submission["problem_id"]] += self.contest_info['penalty_time'] * 60
            row = {
                    "rank": 0,
                    "team_id" : team_id,
                    "score": {
                            "num_solved": num_solved,
                            "total_time": total_time,
                            # "max_submission_id": max_submission_id, # 为什么CCPC没有这个
                            "max_submission_id": 0,
                        },
                    }
            self.scoreboard["rows"].append(row)
        self.scoreboard['rows'].sort(key = lambda x: (-x['score']['num_solved'], x['score']['total_time'], x['score']['max_submission_id']))
        self.scoreboard['rows'][0]['rank'] = 1
        for idx in range(len(self.scoreboard['rows']) - 1):
            self.scoreboard['rows'][idx + 1]['rank'] = idx + 2
            if self.scoreboard['rows'][idx]['score'] == self.scoreboard['rows'][idx + 1]['score']:
                self.scoreboard['rows'][idx + 1]['rank'] = self.scoreboard['rows'][idx]['rank']

        with open("board.csv", "w") as f:
            for row in self.scoreboard['rows']:
                line = f"{self.team_dict[row['team_id']]['name']},{row['score']['num_solved']},{row['score']['total_time'] // 60},{row['rank']}"
                f.write(line + '\n')
    
    def export(self, filename):
        # self.export_XML(filename + '.xml')
        self.export_json(filename + '.json')
        self.export_result(filename + '.csv')

    def export_json(self, filename):
        with open(filename, 'w', encoding="utf-8") as f:
           f.write('\n'.join(self.resolver_json_formatter()))

    def format_json(self, type, id, data):
        return json.dumps({
            'type': type,
            'id': id,
            'data': data
        })

    def resolver_json_formatter(self):
        ret = []
        ret.append(self.format_json('contest', self.contest_info['id'], self.contest_info))
        for judgement_type in self.judgement_types:
            ret.append(self.format_json('judgement-types', judgement_type['id'], judgement_type))
        for group in self.groups.values():
            ret.append(self.format_json('groups', group['id'], group))
        for languages in self.languages:
            ret.append(self.format_json('languages', languages['id'], languages))
        for organization in self.organizations.values():
            ret.append(self.format_json('organizations', organization['id'], organization))
        for team in self.teams:
            ret.append(self.format_json('teams', team['id'], team))
        for problem in self.problems:
            ret.append(self.format_json('problems', problem['id'], problem))
        for submission in self.submissions:
            ret.append(self.format_json('submissions', submission['id'], submission))
        for judgement in self.judgements:
            ret.append(self.format_json('judgements', judgement['id'], judgement))
        # for run in self.runs:
            # ret.append(self.format_json('runs', run['id'], run))
        for award in self.resolver_award_formatter():
            ret.append(self.format_json('awards', award['id'], award))
        ret.append(self.format_json('state', None, self.state_info))
        return ret

    def export_XML(self, filename):
        with open(filename, 'w', encoding="utf-8") as f:
           f.write(XML_dump(self.resolver_formatter()))

    def export_result(self, filename):
        with open(filename, 'w', encoding="utf-8") as f:
           f.write('\n'.join(self.award_list))

    def resolver_formatter(self):
        return { 'contest': self.resolver_contest_formatter() }

    def resolver_contest_formatter(self):
        return {
            'info': self.resolver_info_formatter(),
            'problem': self.resolver_problem_formatter(),
            'region': self.resolver_group_formatter(),
            'team': self.resolver_team_formatter(),
            'judgement': self.resolver_judgement_formatter(),
            'run': self.resolver_run_formatter(),
            'award': self.resolver_award_formatter(),
            # 'finalized': self.resolver_finalized_formatter()
        }

    def resolver_group_formatter(self):
        return [{
            'external-id': group['id'],
            'name': group['name']
        } for group in self.groups.values()]
    
    def resolver_info_formatter(self):
        return {
            'contest-id': self.contest_info['id'],
            'title': self.contest_info['name'],
            # 'short-title': self.contest_info['shortname'],
            'length': self.contest_info['duration'],
            'scoreboard-freeze-length': self.contest_info['scoreboard_freeze_duration'],
            'starttime': dtime2timestamp(self.contest_info['start_time']),
            'penalty': self.contest_info['penalty_time'],
        }

    def resolver_judgement_formatter(self):
        return [{ 
            'acronym': judgement_type['id'] 
        } for judgement_type in self.judgement_types ]

    def resolver_problem_formatter(self):
        return [{ 
            'id': problem['ordinal'] + 1,
            'label': problem['label'],
            'name': problem['name'],
            # 'color': problem['color'],
            # 'rgb': problem['rgb'],
        } for problem in self.problems ]

    def resolver_team_formatter(self):
        return [{
            'id': team['id'],
            'external-id': team['icpc_id'],
            'name': escape(team['name']),
            'university': self.organizations[team['organization_id']]['name'],
            'university-short-name': self.organizations[team['organization_id']]['name'],
            # 'region': self.groups[team['group_ids'][0]]['name'],
        } for team in self.teams ]

    def resolver_run_formatter(self):
        problems = { problem['id']: problem for problem in self.problems }
        return [{
            'id': submission['id'],
            'problem': problems[submission['problem_id']]['ordinal'] + 1,
            'team': submission['team_id'],
            'judged': "true",
            'result': submission['judgement_type']['id'],
            'solved': str(submission['judgement_type']['solved']).lower(),
            'penalty': str(submission['judgement_type']['penalty']).lower(),
            'time': ctime2timestamp(submission['contest_time'])
        } for submission in self.submissions ]

    def resolver_award_formatter(self):
        return reduce(lambda x, y: x + y, [
            # self.resolver_award_winner_formatter(),
            self.resolver_award_top_team_formatter(self.config["ben"]),
            self.resolver_award_top_team_formatter(self.config["zhuan"]),
            self.resolver_award_medal_formatter(self.config["ben"]),
            self.resolver_award_medal_formatter(self.config["zhuan"]),
            # self.resolver_award_best_girl_formatter(),
            # self.resolver_award_first_solved_formatter(),
            # self.resolver_award_last_AC_formatter()
            # self.resolver_award_first_WA()
        ], [])

    def award(self, id, citation, team_ids):
        if type(team_ids) != list:
            teams = [team_ids]
        else:
            teams = team_ids
        for team_id in teams:
            team = self.team_dict[team_id]
            category = self.organizations[team["organization_id"]]["name"]
            group = self.get_team_group_name(team_id)
            members = team["members"]
            self.award_list.append(f'"{team_id}","{team["name"]}","{group}","{category}","{citation}","{members}"')
        return {
            'id': id,
            'citation': citation,
            'show': 'true',
            'team_ids': team_ids
        }

    def get_team_categories_id(self, team_id):
        return self.team_dict[team_id]["group_ids"]

    def team_in_group(self, team_id, check_groups):
        if check_groups == []:
            return True
        check_groups = [str(i) for i in check_groups]
        groups = self.get_team_categories_id(team_id)
        for group_id in groups:
            if str(group_id) in check_groups:
                return True
        return False

    def team_award_occupy(self, team_id):
        return not self.team_in_group(team_id, self.config['no_occupy_award_categories'])

    def get_team_group_name(self, team_id):
        group_name = [] 
        for group_id in self.team_dict[team_id]["group_ids"]:
            group_name.append(self.groups[group_id]["name"])
        return '、'.join(group_name)

    # def resolver_award_first_solved_formatter(self):
    #     first_solved, first_solved_award = [ False for _ in range(len(self.problems)) ], []
    #     problem_id2idx = { problem['id']: problem['ordinal'] for problem in self.problems }
    #     for submission in self.submissions:
    #         if not submission['judgement_type']['solved']:
    #             continue
    #         if not self.team_award_occupy(submission['team_id']): #打星队伍不评奖
    #             continue
    #         if ctime2timestamp(submission['contest_time']) >= ctime2timestamp(self.contest_info['duration']) - ctime2timestamp(self.contest_info['scoreboard_freeze_duration']):
    #             continue
    #         idx = problem_id2idx[submission['problem_id']]
    #         if first_solved[idx]:
    #             continue
    #         first_solved[idx] = True
    #         first_solved_award.append(self.award('first-to-solve-%c' % chr(65 + idx), 'First to solve problem %c' % chr(65 + idx), submission['team_id']))
    #     return first_solved_award

    def resolver_award_top_team_formatter(self, config):  #WARNING: 排名相同无法一起评
        rank = config["first"]
        sign = randomstr(4)
        suffix = config["suffix"]
        award_group = config["group"]
        buf = [[] for _ in range(rank + 1)]
        cnt = 0
        award_school = set()
        for row in self.scoreboard['rows']:
            if cnt == rank:
                break
            if not self.team_in_group(row['team_id'], award_group): 
                continue
            school_id = self.team_dict[row["team_id"]]["organization_id"]
            if school_id in award_school:
                continue
            cnt += 1
            award_school.add(school_id)
            buf[cnt].append(row['team_id'])
        top_team_award = []
        for idx, team_ids in enumerate(buf):
            if idx == 0: continue
            top_team_award.append(self.award(f'rank-{idx}{sign}', f"{make_ordinal_zh(idx)}{suffix}", team_ids))
        return top_team_award

    # def resolver_award_winner_formatter(self):  #WARNING: 排名相同无法一起评
    #     rank = 1
    #     buf = [[] for _ in range(rank + 1)]
    #     cnt = 0
    #     for row in self.scoreboard['rows']:
    #         if cnt == rank:
    #             break
    #         cnt += 1
    #         buf[cnt].append(row['team_id'])
    #     winner_award = []
    #     for _, team_ids in enumerate(buf):
    #         winner_award.append(self.award(f'winner', 'World Champion', team_ids))
    #     return winner_award
    #
    # def resolver_award_best_girl_formatter(self):
    #     best_girls_team_id = -1
    #     for row in self.scoreboard['rows']:
    #         if self.team_in_group(row['team_id'], self.config['award_best_girl']):
    #             best_girls_team_id = row['team_id']
    #             break
    #         if row['rank'] > self.limited: # 限定最佳女队必得奖牌
    #             break
    #     best_girls_award = []
    #     if best_girls_team_id != -1:
    #         best_girls_award.append(self.award(f"group-winner-{self.config['award_best_girl'][0]}", "The Best Girls's Team", best_girls_team_id))
    #     return best_girls_award

    def resolver_award_medal_formatter(self, config):
        medal_team_award = []
        sign = randomstr(4)
        # award for gold
        totle = config['gold']
        suffix = config['suffix']
        buf = []
        pos = 0
        award_school = set()
        up = len(self.scoreboard['rows'])
        if totle > 0:
            while totle > len(award_school) and pos < up:
                row = self.scoreboard['rows'][pos]
                if not self.team_in_group(row['team_id'], config["group"]): 
                    pos += 1
                    continue
                school_id = self.team_dict[row["team_id"]]["organization_id"]
                award_school.add(school_id)
                buf.append(row['team_id'])
                pos += 1
            if buf != []:
                medal_team_award.append(self.award(f"{sign}gold-medal", f"🥇金奖{suffix}", buf))
        # award for silver
        totle += config['silver']
        buf = []
        if totle > 0:
            while totle > len(award_school) and pos < up:
                row = self.scoreboard['rows'][pos]
                if not self.team_in_group(row['team_id'], config["group"]): 
                    pos += 1
                    continue
                school_id = self.team_dict[row["team_id"]]["organization_id"]
                award_school.add(school_id)
                buf.append(row['team_id'])
                pos += 1
            if buf != []:
                medal_team_award.append(self.award(f"{sign}silver-medal", f"🥈银奖{suffix}", buf))
        # award for bronze
        totle += config['bronze']
        buf = []
        if totle > 0:
            while totle > len(award_school) and pos < up:
                row = self.scoreboard['rows'][pos]
                if not self.team_in_group(row['team_id'], config["group"]): 
                    pos += 1
                    continue
                school_id = self.team_dict[row["team_id"]]["organization_id"]
                award_school.add(school_id)
                buf.append(row['team_id'])
                pos += 1
            if buf != []:
                medal_team_award.append(self.award(f"{sign}bronze-medal", f"🥉铜奖{suffix}", buf))
        self.limited = pos - 1
        return medal_team_award

    # def resolver_award_last_AC_formatter(self):
    #     submissions = list(filter(lambda submission: submission['judgement_type']['id'] == "AC", self.submissions))
    #     if len(submissions) == 0:
    #         return []
    #     return [
    #         self.award("last-AC", "Tenacious Award", submissions[-1]['team_id'])
    #     ]
    #
    # def resolver_award_first_WA(self):
    #     submissions = list(filter(lambda submission: submission['judgement_type']['id'] == "WA", self.submissions))
    #     if len(submissions) == 0:
    #         return []
    #     return [
    #         self.award("first-WA", "First WA", submissions[0]['team_id'])
    #     ]

    def resolver_finalized_formatter(self):
        return {
            'last-gold': 0,
            'last-silver': 0,
            'last-bronze': 0,
            'timestamp': 0
        }
