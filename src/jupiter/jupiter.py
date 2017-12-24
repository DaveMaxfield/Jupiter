# coding: utf-8
import json
import copy
import time
import datetime
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../agents')
ABSPATH = os.path.dirname(os.path.abspath(__file__)) + "/../"
from typing import List
import summrizationOfUtilitySpace
import negotiationRule
import display
import agentAction
import comunicateJavaAgent
from linearAgent import*
from boulwareAgent import*
from concederAgent import*

class Jupiter:
    def __init__(self, negotiation_type, negotiation_time: int, setting_file_name, *file_names):
        if negotiation_type == negotiationRule.TypeOfNegotiation.Turn:
            self.__rule = negotiationRule.NegotiationRuleTurn(negotiation_time)
        elif negotiation_type == negotiationRule.TypeOfNegotiation.Time:
            self.__rule = negotiationRule.NegotiationRuleTime(negotiation_time)
        else:
            raise ValueError('negotiation type error in Jupiter init')
        file_names = list(file_names)
        if file_names[0].find("Users") < 0:
            for i in range(0, len(file_names)):
                file_names[i] = ABSPATH + file_names[i]
        self.__utilities = summrizationOfUtilitySpace.SummrizationOfUtilitySpace(file_names)
        self.__setting_file_name = setting_file_name
        self.__file_names = file_names
        self.__agent_list = []

        self.display = display.Display(self.__utilities.get_utility_space(0).get_issue_size_list(),
                                            self.__utilities.get_weight_np_list(),
                                            self.__utilities.get_discount_factor_list(),
                                            self.__utilities.get_reservation_value_list())
        self.__action_list_list = []
        self.__get_agreement_list = []

    def set_agent(self, agent_name):
        instance = globals()[agent_name]
        self.__agent_list.append(instance(
                            self.__utilities.get_utility_space(len(self.__agent_list)),
                            self.__rule,
                            len(self.__agent_list), len(self.__file_names)))
        self.display.set_agent_name(self.__agent_list[-1].get_name())

    def set_name(self, agent_name):
        self.__agent_list.append(LinearAgent(
                            self.__utilities.get_utility_space(len(self.__agent_list)),
                            self.__rule,
                            len(self.__agent_list), len(self.__file_names)))
        self.display.set_agent_name(agent_name)

    def set_java_agent(self, port:int):
        self.__agent_list.append(comunicateJavaAgent.JavaAgent(
                                self.__setting_file_name,
                                self.__utilities.get_utility_space(len(self.__agent_list)),
                                self.__rule,
                                len(self.__agent_list), len(self.__file_names), port))
        self.display.set_agent_name(self.__agent_list[-1].get_name())

    def do_negotiation(self, is_printing: bool, print_times=10) -> bool:
        if self.__rule.get_type() == negotiationRule.TypeOfNegotiation.Turn:
            self.__rule._NegotiationRuleTurn__start_negotiation()
        elif self.__rule.get_type() == negotiationRule.TypeOfNegotiation.Time:
            self.__rule._NegotiationRuleTime__start_negotiation()
        else:
            print('unexpected invalid NegotiationRuleType')
            return False

        if is_printing:
            self.display.plot_initialize()

        print("-" * 30)
        print("start negotiation:", len(self.__get_agreement_list)+1)
        for agent in self.__agent_list:
            agent.receive_start_negotiation()

        action_list = []
        self.__accept_num = 1
        can_proceed = True
        while can_proceed:
            for i in range(len(self.__agent_list)):
                #agentにアクションを起こさせて、時間内かつアクションが有効か検証する
                action = self.__agent_list[i].send_action()
                if self.__rule.get_time_now() > 1.0:
                    return self.__end_negotiation(action_list, [False])
                elif not self.__is_valid_action(action, len(action_list)):
                    print('unexpected invalid action caused')
                    for agent in self.__agent_list:
                        agent.receive_end_negotiation()
                    return False
                elif isinstance(action, agentAction.Accept):
                    action.set_bid(action_list[-1].get_bid())
                action.set_time_offered(self.__rule.get_time_now())
                action_list.append(action)
                # if is_printing:
                # if not isinstance(action, agentAction.EndNegotiation):
                #     print(self.__rule.get_time_now() , self.__agent_list[action.get_agent_id()].get_name(),
                #         action_list[-1].__class__.__name__, action_list[-1].get_bid().get_indexes())
                #各agentにアクションを知らせる
                for j in range(len(self.__agent_list)):
                    if i == j:
                        continue
                    self.__agent_list[j].receive_action(action_list[-1])
                #ネゴシエーションの終了判定
                if self.__is_finished_negotiation(action):
                    if is_printing:
                        self.display.update_end(action_list, [True, action])
                    # EndNegotiationもprato_distanceをだせるように
                    if not isinstance(action, agentAction.EndNegotiation):
                        print("last turn:", self.__rule.get_time_now())
                        print("agreement bid:", action.get_bid().get_indexes())
                        print("parato distance:",self.display.get_parato_distance(action))
                        for j, agent in enumerate(self.__agent_list):
                            print(agent.get_name(), ":", self.__utilities.get_utility_space(j)
                                .get_utility_discounted(action.get_bid(), action.get_time_offered()))
                    else:
                        print("last turn:", self.__rule.get_time_now())
                        print("agreement bid: EndNegotiation")
                    # EndNegotiationもprato_distanceをだせるように
                    return self.__end_negotiation(action_list, [True, action])
                elif self.__rule.get_type() == negotiationRule.TypeOfNegotiation.Time and \
                    not self.__rule._NegotiationRuleTime__proceed_negotiation():
                    return self.__end_negotiation(action_list, [False])
            if is_printing and len(action_list) % print_times == 0:
                self.display.update(action_list)
            if self.__rule.get_type() == negotiationRule.TypeOfNegotiation.Turn:
                can_proceed = self.__rule._NegotiationRuleTurn__proceed_negotiation()
        print("fail to get agreement")
        return self.__end_negotiation(action_list, [False])

    def __is_valid_action(self, action: agentAction.AbstractAction, action_len: int) -> bool:
        if isinstance(action, agentAction.Accept) and action_len == 0:
            raise ValueError('first accept error in agent_id:',action.get_agent_id())
        elif isinstance(action, agentAction.Offer) and not self.__utilities.is_valid_bid(action.get_bid()):
            raise ValueError('bid index error in agent_id:',action.get_agent_id())
        return True

    def __is_finished_negotiation(self, action: agentAction.AbstractAction) -> bool:
        if isinstance(action, agentAction.EndNegotiation):
            return True
        elif isinstance(action, agentAction.Accept):
            self.__accept_num += 1
            if self.__accept_num == len(self.__agent_list):
                return True
        else:
            self.__accept_num = 1
        return False

    def __end_negotiation(self, actions, agreement) -> bool:
        for agent in self.__agent_list:
            agent.receive_end_negotiation()
        self.__action_list_list.append(actions)
        self.__get_agreement_list.append(agreement)
        return True

    def display_points_end(self):
        if len(self.__agent_list) == 3:
            self.display.display_plot3_update_end(self.__action_list_list[-1], self.__get_agreement_list[-1])
        elif len(self.__agent_list) == 2:
            self.display.display_plot2_update_end(self.__action_list_list[-1], self.__get_agreement_list[-1])

    # def display(self):
    #     self.display.show()

    def set_save_pictures_Flag(self):
        self.display.set_save_flag()

    def set_notebook_flag(self):
        self.display.set_jupyter_notebook_flag()

    def save_history_as_json(self):
        def action_to_dict(action: agentAction.AbstractAction):
            action_dict = {}
            if isinstance(action, agentAction.Accept):
                action_dict["type"] = "accept"
                action_dict["bid"] = action.get_bid().get_indexes()
            elif isinstance(action, agentAction.Offer):
                action_dict["type"] = "offer"
                action_dict["bid"] = action.get_bid().get_indexes()
            elif isinstance(action, agentAction.EndNegotiation):
                action_dict["type"] = "end_negotiation"
            action_dict["id"] = action.get_agent_id()
            action_dict["time"] = action.get_time_offered()
            return action_dict

        history_dictionary = {}
        history_dictionary["agents"] = {}
        history_dictionary["agents"]["setting"] = self.__setting_file_name
        history_dictionary["agents"]["size"] = len(self.__agent_list)
        for agent, (i, file_name) in zip(self.__agent_list, enumerate(self.__file_names)):
            history_dictionary["agents"][i] = {}
            history_dictionary["agents"][i]["agent_name"] = agent.get_name()
            history_dictionary["agents"][i]["file_name"] = file_name
            history_dictionary["agents"][i]["id"] = i

        history_dictionary["rule"] = {}
        history_dictionary["rule"]["period"] = self.__rule.get_time_max()
        history_dictionary["rule"]["repeating"] = len(self.__get_agreement_list)
        if self.__rule.get_type() == negotiationRule.TypeOfNegotiation.Turn:
            history_dictionary["rule"]["type"] = "turn"
        elif self.__rule.get_type() == negotiationRule.TypeOfNegotiation.Time:
            history_dictionary["rule"]["type"] = "time"

        for agreement, (i, action_list) in zip(self.__get_agreement_list ,enumerate(self.__action_list_list, start=1)):
            history_dictionary[i] = {}
            history_dictionary[i]["result"] = {}
            if len(agreement) == 2:
                history_dictionary[i]["result"]["action"] = action_to_dict(agreement[1])
            history_dictionary[i]["result"]["is_successful"] = agreement[0]
            history_dictionary[i]["result"]["period"] = len(action_list)

            for j, action in enumerate(action_list, start=1):
                history_dictionary[i][j] = action_to_dict(action)

        #print(history_dictionary)
        time_now = datetime.datetime.now().strftime('%Y%m%d-%H:%M:%S')
        print("save in " + ABSPATH + 'log/bids' + time_now + ".json")
        f = open(ABSPATH + 'log/bids' + time_now + ".json", 'w')
        json.dump(history_dictionary, f, indent=4)
        return True

    def get_agent_num(self):
        return len(self.__agent_list)
    def get_utility(self, index, bid_, time_):
        return self.__utilities.get_utility_space(index).get_utility_discounted(bid_, time_)

def display_log(file_name, number_of_repeating):
    def set_jupiter(history_dictionary):
        if history_dictionary['rule']['type'] == 'turn':
            negotiation_type = negotiationRule.TypeOfNegotiation.Turn
        elif history_dictionary['rule']['type'] == 'time':
            negotiation_type = negotiationRule.TypeOfNegotiation.Time
        negotiation_time = history_dictionary['rule']['period']
        setting_file_name = history_dictionary["agents"]['setting']
        file_list = []
        for i in range(0, history_dictionary["agents"]["size"]):
            file_list.append(history_dictionary["agents"][str(i)]["file_name"])
        # file2 = history_dictionary["agents"]["1"]["file_name"]
        # file3 = history_dictionary["agents"]["2"]["file_name"]
        if history_dictionary["agents"]["size"] == 2:
            jupiter = Jupiter(negotiation_type, negotiation_time, setting_file_name, file_list[0], file_list[1])
        elif history_dictionary["agents"]["size"] == 3:
            jupiter = Jupiter(negotiation_type, negotiation_time, setting_file_name, file_list[0], file_list[1], file_list[2])
        for i in range(0, history_dictionary["agents"]["size"]):
            jupiter.set_name(history_dictionary["agents"][str(i)]["agent_name"])
        # jupiter.set_agent(history_dictionary["agents"]["1"]["agent_name"])
        # jupiter.set_agent(history_dictionary["agents"]["2"]["agent_name"])
        return jupiter

    def dict_to_action(action_dict:dict):
        if action_dict["type"] == "accept":
            action = agentAction.Accept(action_dict["id"])
            action.set_bid(bid.Bid(action_dict["bid"]))
            action.set_time_offered(action_dict["time"])
        elif action_dict["type"] == "offer":
            action = agentAction.Offer(action_dict["id"], bid.Bid(action_dict["bid"]))
            action.set_time_offered(action_dict["time"])
        elif action_dict["type"] == "end_negotiation":
            action = agentAction.EndNegotiation(action_dict["id"])
        return action

    f = open(file_name , 'r')
    history_dictionary = json.load(f)
    jupiter = set_jupiter(history_dictionary)

    jupiter.display.plot_initialize()
    # last_history = history_dictionary[str(history_dictionary["rule"]["repeating"])]
    last_history = history_dictionary[str(number_of_repeating)]
    action_list = []
    for i in range(1, last_history["result"]["period"]+1):
        action_list.append(dict_to_action(last_history[str(i)]))
        jupiter.display.update(action_list)

    if last_history["result"]["is_successful"]:
        jupiter.display.update_end(action_list, [True, action_list[-1]])
    else:
        jupiter.display.update_end(action_list, [False])
    print("agreement bid:", action_list[-1].get_bid().get_indexes())
    print("parato distance:", jupiter.display.get_parato_distance(action_list[-1]))
    for i in range(0, jupiter.get_agent_num()):
        print(history_dictionary["agents"][str(i)]["agent_name"], ":", jupiter.get_utility(i, action_list[-1].get_bid(), action_list[-1].get_time_offered()))
    jupiter.display.show()


if __name__ == '__main__':
    pass
    # jupiter = Jupiter(negotiationRule.TypeOfNegotiation.Turn, 180, 'domain/Atlas3/triangularFight.xml',
    #     'domain/Atlas3/triangularFight_util1.xml', 'domain/Atlas3/triangularFight_util2.xml')
    # jupiter.set_agent('LinearAgent')
    #jupiter.set_agent('ImprovementAgent')
    # jupiter.set_agent('LinearAgent')
    #jupiter.set_agent('ConcederAgent')
    # jupiter.set_agent('BoulwareAgent')
    # jupiter.set_agent('LinearAgent')
    # jupiter.set_agent('ConcederAgent')
    # jupiter.set_agent('BoulwareAgent')
    # jupiter.set_java_agent(25535)

    #jupiter.test()
    #jupiter.set_save_pictures_Flag()
    #jupiter.set_notebook_flag()
    # jupiter.display.show()
    # jupiter.display.show()
    # jupiter.save_history_as_json()
    # display_log("log/bids20171222-12:10:32.json", 1)
    # jupiter.do_negotiation(is_printing=True, print_times=1)
    # jupiter.display.show()
    # jupiter.save_history_as_json()
    # display_log("log/bids20171222-15:37:21.json", 1)
    #jupiter.do_negotiation(is_printing=True, print_times=1)
    #jupiter.display()