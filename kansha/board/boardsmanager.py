# -*- coding:utf-8 -*-
#--
# Copyright (c) 2012-2014 Net-ng.
# All rights reserved.
#
# This software is licensed under the BSD License, as described in
# the file LICENSE.txt, which you should have received as part of
# this distribution.
#--
import json
import os.path
from glob import glob

from kansha.card.fts_schema import Card as FTSCard
from .models import DataBoard


class BoardsManager(object):
    def create_board(self, template_path, user):
        """Create new board

        In:
            - ``template_path`` -- path to the JSON template
            - ``user`` -- owner of the board (UserData instance)
        Return:
            - new DataBoard created
        """
        with open(template_path, 'r') as f:
            tpl = json.loads(f.read())
        return DataBoard.from_template(tpl, user)

    def get_by_id(self, id):
        return DataBoard.get(id)

    def get_by_uri(self, uri):
        return DataBoard.get_by_uri(uri)

    @staticmethod
    def index_user_cards(user, search_engine):
        for card in user.my_cards:
            search_engine.add_document(FTSCard.from_model(card))
        search_engine.commit()

    @staticmethod
    def create_boards_from_templates(user, folder):
        '''user is a DataUser'''
        for tplf_name in glob(os.path.join(folder, '*.btpl')):
            with open(tplf_name, 'r') as f:
                tpl = json.loads(f.read())
                DataBoard.from_template(tpl, user)
