# -*- coding:utf-8 -*-
#--
# Copyright (c) 2012-2014 Net-ng.
# All rights reserved.
#
# This software is licensed under the BSD License, as described in
# the file LICENSE.txt, which you should have received as part of
# this distribution.
#--

from datetime import date, datetime
import time

from elixir import using_options
from elixir import ManyToMany, ManyToOne, OneToMany, OneToOne
from elixir import Field, Unicode, Integer, DateTime, Date, UnicodeText
from sqlalchemy.orm import subqueryload
from nagare.database import session
import datetime

from kansha.models import Entity
from kansha.comment.models import DataComment
from kansha.checklist.models import DataChecklist, DataChecklistItem


class DataCard(Entity):

    """Card mapper
    """
    using_options(tablename='card')
    title = Field(UnicodeText)
    description = Field(UnicodeText, default=u'')
    votes = OneToMany('DataVote')
    index = Field(Integer)
    column = ManyToOne('DataColumn')
    labels = ManyToMany('DataLabel')
    comments = OneToMany('DataComment', order_by="-creation_date")
    assets = OneToMany('DataAsset', order_by="-creation_date")
    checklists = OneToMany('DataChecklist', order_by="index")
    members = ManyToMany('DataUser')
    cover = OneToOne('DataAsset', inverse="cover")
    author = ManyToOne('DataUser', inverse="my_cards")
    creation_date = Field(DateTime)
    due_date = Field(Date)
    history = OneToMany('DataHistory')
    weight = Field(Unicode(255), default=u'')

    def delete_history(self):
        for event in self.history:
            session.delete(event)
        session.flush()

    @classmethod
    def create_card(cls, column, title, user):
        """Create new column

        In:
            - ``column`` -- DataColumn, father of the column
            - ``title`` -- title of the card
            - ``user`` -- DataUser, author of the card
        Return:
            - created DataCard instance
        """
        new_card = cls(title=title, author=user,
                       creation_date=datetime.datetime.utcnow())
        column.cards.append(new_card)
        return new_card

    @classmethod
    def delete_card(cls, card):
        """Delete card

        Delete a given card and re-index other cards

        In:
            - ``card`` -- DataCard instance to delete
        """
        index = card.index
        column = card.column
        card.delete()
        session.flush()
        # legacy databases may be broken…
        if index is None:
            return
        q = cls.query
        q = q.filter(cls.index >= index)
        q = q.filter(cls.column == column)
        q.update({'index': cls.index - 1})

    @classmethod
    def get_all(cls):
        query = cls.query.options(subqueryload('labels'), subqueryload('comments'))
        return query

    def make_cover(self, asset):
        """
        """
        DataCard.get(self.id).cover = asset.data

    def remove_cover(self):
        """
        """
        DataCard.get(self.id).cover = None

    def remove_board_member(self, member):
        """Remove member from board"""
        if member.get_user_data() in self.members:
            self.members.remove(member.get_user_data())
            session.flush()

    @classmethod
    def from_template(cls, data, user, labels):
        card = cls(title=data.get('title', u''),
                   description=data.get('description', u''),
                   creation_date=datetime.datetime.utcnow(),
                   author=user)

        due_date = data.get('due_date')
        if due_date is not None:
            due_date = time.strptime(due_date, '%Y-%m-%d')
            due_date = date(*due_date[:3])
            card.due_date = due_date

        for comment in data.get('comments', ()):
            DataComment(comment=comment,
                        creation_date=datetime.datetime.utcnow(),
                        card=card,
                        author=user)

        for checklist in data.get('checklists', ()):
            items = checklist.get('items', ())
            checklist = DataChecklist(title=checklist.get('title', u''),
                                      card=card)
            for item in items:
                DataChecklistItem(title=item.get('title', u''),
                                  done=item.get('done', False),
                                  checklist=checklist)

        for label in data.get('labels', ()):
            label = labels.get(label)
            if label is not None:
                card.labels.append(label)
        return card

    def to_template(self):
        ret = {'title': self.title,
               'description': self.description,
               'comments': [],
               'labels': [],
               'checklists': [],
               'due_date': None}
        if self.due_date:
            ret['due_date'] = self.due_date.strftime('%Y-%m-%d')
        for comment in self.comments:
            ret['comments'].append(comment.comment)

        for checklist in self.checklists:
            ck = {'title': checklist.title,
                  'items': []}
            for item in checklist.items:
                ck['items'].append({'title': item.title,
                                    'done': item.done})
            ret['checklists'].append(ck)

        for label in self.labels:
            ret['labels'].append(label.title)

        return ret
