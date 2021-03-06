# -*- coding:utf-8 -*-
#--
# Copyright (c) 2012-2014 Net-ng.
# All rights reserved.
#
# This software is licensed under the BSD License, as described in
# the file LICENSE.txt, which you should have received as part of
# this distribution.
#--
"""
Trans-board view of user's cards
"""

from itertools import groupby
from sqlalchemy import desc

from nagare import (component, presentation, i18n)
from kansha.card import comp as card
from kansha.card.models import DataCard
from kansha.column.models import DataColumn
from kansha.board.models import DataBoard


class UserCards(object):

    # the lambdas on the fields are there to avoid serialization
    KEYS = {
        'board': (lambda: DataBoard.title, lambda c: (c().data.column.board.title,
                                                      c().data.column.board.id)),
        'column': (lambda: DataColumn.index, lambda c: c().data.column.title),
        'due': (lambda: desc(DataCard.due_date), lambda c: c().data.due_date)
    }

    def __init__(self, user, search_engine, theme, services_service):
        """
        In:
         - ``user`` -- DataUser instance
        """
        self.user = user
        self._services = services_service
        self.search_engine = search_engine
        self.order_by = ('board', 'column')
        self.theme = theme

    @property
    def order_by(self):
        return self._order_by

    @order_by.setter
    def order_by(self, v):
        self._cards = None
        self._order_by = v

    @property
    def user(self):
        if not self._user:
            self._user = self._get_user()
        return self._user

    @user.setter
    def user(self, value):
        self._user = value
        self._get_user = lambda cls = value.__class__, id_ = value._sa_instance_state.key[1]: cls.get(id_)

    def __getstate__(self):
        state = self.__dict__
        state['_user'] = None
        return state

    @property
    def cards(self):

        if self._cards is None:
            order_keys = [self.KEYS[feat] for feat in self.order_by]
            order = [prop() for prop, __ in order_keys]
            self._cards = [
                component.Component(
                    self._services(card.Card, c.id, None, {}, data=c)
                )
                # FIXME: nosql in components!
                for c in (self.user.cards.join(DataCard.column).
                          join(DataColumn.board).
                          filter(DataColumn.archive==False).
                          filter(DataBoard.id.in_(b.id for b in self.user.boards)).
                          order_by(*order))
            ]
            # TODO: instead of filtering allowed boards here, we should define and implement
            # a policy for what should happen when a user is removed from a board. Should we
            # remove her from all the cards?
        return self._cards


@presentation.render_for(UserCards)
def render(self, h, comp, *args):
    h.head.css_url('css/themes/home.css')
    h.head.css_url('css/themes/board.css')
    h.head.css_url('css/themes/%s/home.css' % self.theme)
    h.head.css_url('css/themes/%s/board.css' % self.theme)

    with h.div(class_='row', id_='lists'):
        i = 1
        for main_group, cards in groupby(self.cards, key=self.KEYS[self.order_by[0]][1]):
            subgroup = None
            sg_title = self.KEYS[self.order_by[1]][1]
            with h.div(class_='span-auto list'):
                with h.div(class_='list-header'):
                    with h.div(class_='list-title'):
                        with h.div(class_='title'):
                            if isinstance(main_group, tuple):
                                title, id_ = main_group
                                with h.a.action(comp.answer, id_):
                                    h << title
                            else:
                                h << (unicode(main_group) if main_group else i18n._(u'n.c.'))
                with h.div(class_='list-body'):
                    for card in cards:
                        if subgroup != sg_title(card):
                            subgroup = sg_title(card)
                            h << h.h4(subgroup)
                        h << card.render(h, 'readonly')
                h << h.div(class_='list-footer hidden')
            if i % 4 == 0:
                h << h.br
            i += 1
    return h.root
