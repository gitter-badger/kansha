# -*- coding:utf-8 -*-
#--
# Copyright (c) 2012-2014 Net-ng.
# All rights reserved.
#
# This software is licensed under the BSD License, as described in
# the file LICENSE.txt, which you should have received as part of
# this distribution.
#--

from nagare import ajax
from nagare import component, var, security, i18n
from nagare.i18n import _

from .models import DataColumn
from ..toolbox import popin, overlay
from ..card import (comp as card, fts_schema)
from ..title import comp as title
from ..card.models import DataCard
from .. import exceptions, notifications


class Column(object):

    """Column component
    """

    def __init__(self, id_, board, card_extensions, search_engine, services_service, data=None):
        """Initialization

        In:
            - ``id_`` -- the id of the column
        """
        self.db_id = id_
        self._data = data
        self.id = 'list_' + str(self.db_id)
        self.board = board
        self.nb_card = var.Var(self.data.nb_max_cards)
        self._services = services_service
        self.search_engine = search_engine
        self.card_extensions = card_extensions
        self.body = component.Component(self, 'body')
        self.title = component.Component(ColumnTitle(self))
        self.title.on_answer(lambda v: self.title.call(model='edit'))
        self.card_counter = component.Component(CardsCounter(self))
        self.cards = [component.Component(self._services(card.Card, c.id, self, self.card_extensions, data=c))
                      for c in self.data.cards]
        self.new_card = component.Component(
            card.NewCard(self)).on_answer(self.create_card)

        self.actions_comp = component.Component(self, 'overlay')
        self.actions_overlay = component.Component(overlay.Overlay(
            lambda r: r.i(class_='icon-circle-down'),
            self.actions_comp.render,
            title=_('List actions'), dynamic=False))

    def copy(self, parent, additional_data):
        new_data = self.data.copy(parent.data)
        new_obj = self._services(Column, new_data.id, None, self.card_extensions, self.search_engine, data=new_data)

        for card in self.cards:
            new_card = card().copy(new_obj, additional_data)
            new_obj.cards.append(component.Component(new_card))

        return new_obj

    def set_reload_search(self):
        self.board.set_reload_search()

    def actions(self, data, comp):
        if data[0] == 'delete':
            comp.answer(data[1])
        elif data[0] == 'set_limit':
            self.card_counter.call(model='edit')
        elif data[0] == 'purge':
            for card in self.cards:
                self.delete_card(card())
            self.reload()
        self.set_reload_search()

    @property
    def data(self):
        """Return the column object from the database
        """
        if self._data is None:
            self._data = DataColumn.get(self.db_id)
        return self._data

    def __getstate__(self):
        self._data = None
        return self.__dict__

    def set_title(self, title):
        """Set title

        In:
            - ``title`` -- new title
        """
        self.data.title = title

    def get_title(self):
        """Get title

        Return :
            - the board title
        """
        if self.is_archive:
            return i18n._(u'Archived cards')
        return self.data.title

    @property
    def favorites(self):
        """Return favorites users for a given column

        Ask favorites to board

        Return:
            - a dictionary {'username', 'nb used'}
        """
        return self.board.favorites

    def get_most_used_users(self):
        """Return the most used users in this column

        Return:
            - a dictionary {'username', 'nb used'}
        """
        most_used_users = {}
        for c in self.cards:
            # Test if c() is a Card instance and not Popin instance
            if isinstance(c(), card.Card):
                for m in c().members:
                    username = m.username
                    most_used_users[username] = most_used_users.get(username, 0) + 1
        return most_used_users

    def remove_board_member(self, member):
        """Remove member from board

        Remove member from board. If member is PendingUser then remove
        invitation.

        In:
            - ``member`` -- Board Member instance to remove
        """
        for c in self.cards:
            if isinstance(c(), card.Card):
                c().remove_board_member(member)

    def get_authorized_users(self):
        """Return users authorized to be add on this column"""
        return set(self.board.get_authorized_users())

    def get_pending_users(self):
        return set(self.board.get_pending_users())

    def delete(self):
        """Delete itself"""
        for card in self.cards:
            self.archive_card(card())
        DataColumn.delete_column(self.data)

    def move_cards(self, cards):
        """Replace self.cards by cards

        In:
            - ``cards`` -- list of Card instances wrapped on component
        """

        self.cards = cards
        # remove cards for data part
        self.data.cards = []
        for card_index, card in enumerate(cards):
            card().move_card(card_index, self)

    def move_card(self, card_id, index):
        found = False
        for card_index, card in enumerate(self.data.cards):
            if 'card_%s' % card.id == card_id:
                found = True
                break
        if not found:
            raise ValueError(u'Card has been deleted or does not belong to this list anymore')
        data_column = self.data
        card = data_column.cards.pop(card_index)
        data_column.cards.insert(index, card)
        self.reorder()
        card = self.cards.pop(card_index)
        self.cards.insert(index, card)

    def reorder(self):
        self.data.reorder()

    def remove_card(self, card_id):
        found = False
        for card_index, card in enumerate(self.cards):
            if card().id == card_id:
                found = True
                break
        if not found:
            raise ValueError(u'Card has been deleted or does not belong to this list anymore')
        removed_card = self.cards.pop(card_index)
        self.reorder()
        return removed_card

    def insert_card(self, card, index):
        self.cards.insert(index, card)
        card().move_card(index, self)
        data_column = self.data
        c = data_column.cards
        c.remove(card().data)
        c.insert(index, card().data)
        self.reorder()

    def get_available_labels(self):
        return self.board.labels

    def change_index(self, new_index):
        """Change index of the column

        In:
            - ``index`` -- new index
        """
        self.data.index = new_index

    def create_card(self, text=''):
        """Create a new card

        In:
            - ``text`` -- the title of the new card
        """
        if text:
            if self.can_add_cards:
                new_card = self.data.create_card(text, security.get_user().data)
                card_obj = self._services(card.Card, new_card.id, self, self.card_extensions)
                self.cards.append(component.Component(card_obj, 'new'))
                values = {'column_id': self.id,
                          'column': self.title().text,
                          'card': new_card.title}
                notifications.add_history(self.board.data, new_card,
                                          security.get_user().data,
                                          u'card_create', values)
                scard = fts_schema.Card.from_model(new_card)
                self.search_engine.add_document(scard)
                self.search_engine.commit()
                self.set_reload_search()
                return card_obj
            else:
                raise exceptions.KanshaException(_('Limit of cards reached fo this list'))

    def delete_card(self, c):
        """Delete card

        In:
            - ``c`` -- card to delete
        """
        self.cards = [card for card in self.cards if c != card()]
        values = {'column_id': self.id, 'column': self.title().text, 'card': c.title().text}
        notifications.add_history(self.board.data, c.data,
                                  security.get_user().data,
                                  u'card_delete', values)
        self.search_engine.delete_document(fts_schema.Card, c.id)
        self.search_engine.commit()
        c.delete()

    def reload(self):
        self.cards = [component.Component(
            self._services(card.Card, c.id, self, self.card_extensions, data=c)
            ) for c in self.data.cards]

    def archive_card(self, c):
        """Delete card

        In:
            - ``c`` -- card to delete
        """
        self.cards = [card for card in self.cards if c != card()]
        values = {'column_id': self.id, 'column': self.title().text, 'card': c.title().text}
        notifications.add_history(self.board.data, c.data, security.get_user().data, u'card_archive', values)
        self.board.archive_card(c)

    def edit_card(self, c):
        """Wraps a card component into a popin component.

        In:
            - ``c`` -- card to edit (or delete)

        """
        if c.call(popin.Popin(c, 'edit')) == 'delete':
            self.archive_card(c())
        scard = fts_schema.Card.from_model(c().data)
        self.search_engine.update_document(scard)
        self.search_engine.commit()
        c().reload()
        self.set_reload_search()

    def set_nb_cards(self, nb_cards):

        self.data.nb_max_cards = int(nb_cards) if nb_cards else None

    @property
    def can_add_cards(self):
        rval = True
        if self.nb_max_cards is not None:
            rval = self.count_cards < self.nb_max_cards
        return rval

    @property
    def nb_max_cards(self):
        return self.data.nb_max_cards

    @property
    def count_cards(self):
        return self.data.get_cards_count()

    @property
    def is_archive(self):
        return self.data.archive


class NewColumn(object):

    """Column creator component
    """

    def __init__(self, board):
        """Initialization

        In:
            - ``board`` -- the board the new column will belong
        """
        self.board = board
        self.index = var.Var()
        self.title = var.Var()
        self.nb_cards = var.Var()
        self.nb_cards_comp = component.Component(self, 'nb_cards')

    def count_board_columns(self):
        """Return the number of columns in the board
        """
        return len(self.board.columns)

    def create_column(self, comp):
        """Create the column.

        Create new column and call the model "closed" on component

        In:
            - ``comp`` -- component
        """
        nb_cards = int(self.nb_cards()) if self.nb_cards() else None
        col = self.board.create_column(self.index(), self.title(), nb_cards or None)
        col_id = 'list_' + str(col.id)

        return (
            "YAHOO.kansha.app.toggleMenu('boardNavbar');"
            "reload_columns();"
            "YAHOO.kansha.app.saveLimit(%s,%s)" % (
                ajax.py2js(col_id), ajax.py2js(nb_cards or 0)
            )
        )


class ColumnTitle(title.Title):

    """Column title component
    """
    model = DataColumn
    field_type = 'input'


class CardsCounter(object):

    def __init__(self, column):
        self.column = column
        self.id = self.column.id + '_counter'
        self.text = self.get_label()
        self.error = None

    def get_label(self):
        if self.column.nb_max_cards:
            label = str(self.column.count_cards) + '/' + str(self.column.nb_max_cards)
        else:
            label = str(self.column.count_cards)
        return label

    def change_nb_cards(self, text):
        """Change the title of our wrapped object

        In:
            - ``text`` -- the new title
        Return:
            - the new title

        """

        self.text = text
        self.column.set_nb_cards(text)
        return text

    def reset_error(self):
        self.error = None

    def cancel(self, comp):
        self.reset_error()
        comp.answer()

    def validate(self, text, comp):
        self.reset_error()
        nb = int(text) if text else 0
        count = self.column.count_cards
        if not nb:
            comp.answer(self.change_nb_cards(nb))
        elif nb >= count:
            comp.answer(self.change_nb_cards(nb))
        else:
            self.error = _('Must be bigger than %s') % count
