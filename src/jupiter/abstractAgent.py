# coding: utf-8
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/agents')
from abc import ABCMeta, abstractmethod
import abstractUtilitySpace
import negotiationRule
import agentAction

# 抽象クラス
class AbstractAgent(metaclass=ABCMeta):
    """
    交渉参加エージェントの抽象クラス
    全交渉エージェントはこのクラスを継承すること
    """

    @abstractmethod
    def __init__(self, utility_space: abstractUtilitySpace.AbstractUtilitySpace,
                negotiation_rule: negotiationRule.NegotiationRule, agent_id:int, agent_num:int):
        """
        初期化処理が行われる
        utility_space 効用空間の情報が取得できる
        negotiation_rule 交渉の時間やタイプ，現在の正規化時間が取得できる
        agent_id 自分のエージェントに割り振られたid
        agent_num 交渉参加エージェントの数
        """
        pass

    @abstractmethod
    def receive_action(self, agent_action: agentAction.AbstractAction):
        """他エージェントが行動を起こした場合に，その行動が通知される"""
        pass
    @abstractmethod
    def send_action(self) -> agentAction.AbstractAction:
        """自分のターンが回ってきた際に呼び出され，どの行動を起こすか返す"""
        pass
    @abstractmethod
    def get_name(self) -> str:
        """自分のエージェントの名前を返す．クラス名と同じにすることを推奨"""
        pass

    def receive_start_negotiation(self):
        """提案応答ゲームを行う際に，提案応答ゲームが開始される際に呼び出される"""
        pass

    def receive_end_negotiation(self):
        """提案応答ゲームを行う際に，提案応答ゲームが終了される際に呼び出される"""
        pass


if __name__ == "__main__":
    pass