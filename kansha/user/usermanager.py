# -*- coding:utf-8 -*-
#--
# Copyright (c) 2012-2014 Net-ng.
# All rights reserved.
#
# This software is licensed under the BSD License, as described in
# the file LICENSE.txt, which you should have received as part of
# this distribution.
#--
import random
from datetime import datetime, timedelta

from nagare.namespaces import xhtml
from nagare import component, database, i18n

from kansha.toolbox import autocomplete
from .models import DataUser
from .comp import User


class UserManager(object):

    @classmethod
    def get_app_user(cls, username, data=None):
        """Return User instance"""
        if not data:
            data = cls.get_by_username(username)
        if data.source != 'application':
            # we need to set a passwd for nagare auth
            user =  User(username, 'passwd', data=data)
        else:
            user = User(username, data=data)
        return user

    @staticmethod
    def search(value):
        """Return all users which name begins by value"""
        return DataUser.search(value)

    @staticmethod
    def get_all_users(hours=0):
        """Return all data users if `hours` is 0 or just those who have registrated
        for the last hours."""
        q = DataUser.query
        if hours:
            since = datetime.utcnow() - timedelta(hours=hours)
            q = q.filter(DataUser.registration_date >= since)
        return q.all()

    @staticmethod
    def get_by_username(username):
        return DataUser.get_by_username(username)

    @staticmethod
    def get_by_email(email):
        return DataUser.get_by_email(email)

    @staticmethod
    def get_unconfirmed_users(before_date):
        """Return unconfirmed user

        Return all user which have'nt email validated before a date
        In:
            - ``before_date`` -- limit date
        Return:
            - list of DataUser instance
        """
        return DataUser.get_unconfirmed_users(before_date)

    @staticmethod
    def get_confirmed_users():
        """Return confirmed user

        Return all user which have email validated

        Return:
            - list of DataUser instance
        """
        return DataUser.get_confirmed_users()

    def create_user(self, username, password, fullname, email,
                    source=u'application', picture=None):
        from ..authentication.database import forms
        user = DataUser(username, password, fullname, email,
                        source, picture, language=i18n.get_locale().language)
        token_gen = forms.TokenGenerator(email, u'invite board')
        for token in token_gen.get_tokens():
            if token_gen.check_token(token.token) and token.board:
                user.add_board(token.board)
            token_gen.reset_token(token.token)
        return user

    def populate(self):
        from kansha.board.models import DataBoard

        data = {
            "title": u"Todo list",
            "labels": [
                {"title": u"Green", "color": u"#22C328"},
                {"title": u"Red", "color": u"#CC3333"},
                {"title": u"Blue", "color": u"#3366CC"},
                {"title": u"Yellow", "color": u"#D7D742"},
                {"title": u"Orange", "color": u"#DD9A3C"},
                {"title": u"Purple", "color": u"#8C28BD"}
            ],
            "columns": [
                {"title": u"Todo",
                 "cards": [{"title": u"Get some milk",
                            "labels": ["Green"]},
                           {"title": u"Pay bills",
                            "labels": ["Green", "Blue"]},
                           {"title": u"Call grandma",
                            "labels": ["Yellow"]},]},
                {"title": u"Doing",
                 "cards": [{"title": u"Bathroom paint",
                            "labels": ["Green"]}]},
                {"title": u"Done",
                 "cards": [{"title": u"Repair the car"},]}
            ]
        }

        user1 = self.create_user(
            u'user1', u'password', u'user 1', u'user1@net-ng.com')
        user1.confirm_email()
        DataBoard.from_template(data, user1)

        user2 = self.create_user(
            u'user2', u'password', u'user 2', u'user2@net-ng.com')
        user2.confirm_email()
        DataBoard.from_template(data, user2)

        user3 = self.create_user(
            u'user3', u'password', u'user 3', u'user3@net-ng.com')
        user3.confirm_email()
        DataBoard.from_template(data, user3)

        user1.boards[0].title = u"Welcome Board User1"
        user2.boards[0].title = u"Welcome Board User2"
        user3.boards[0].title = u"Welcome Board User3"

        # Share boards and cards for tests
        user1.boards[0].members.extend([user2, user3])
        user2.boards[0].members.append(user1)
        user1.boards[0].columns[0].cards[2].members = [user1, user2]
        user1.boards[0].columns[0].cards[0].members = [user3]
        user2.boards[0].columns[1].cards[0].members = [user1, user2]

        # Add comment from other user
        for u1, u2 in ((user1, user2),
                       (user2, user3),
                       (user3, user1)):
            from ..comment.models import DataComment
            u1.boards[0].columns[0].cards[-1].comments.append(DataComment(comment=u"I agree.",
                                                                          creation_date=datetime.utcnow(),
                                                                          author=u2))

###### TODO: Move the defintions below somewhere else ##########

class NewMember(object):

    """New Member Class"""

    def __init__(self, autocomplete_method):
        """Init method

        In:
            - ``autocomplete_methode`` -- method called for autocomplete
        """
        self.text_id = 'new_members_' + str(random.randint(10000000, 99999999))
        self.autocomplete = component.Component(
            autocomplete.Autocomplete(self.text_id, self.autocompletion, delimiter=','))
        self.autocomplete_method = autocomplete_method

    def autocompletion(self, value, static_url):
        """Return users with email which match with value.

        Method called by autocomplete. This method returns a list of tuples.
        First element of tuple is the email's user. The second is a HTML
        fragment to display in the list of matches.

        In:
         - ``value`` -- first letters of user email
        Return:
         - list of tuple (email, HTML string)
        """
        h = xhtml.Renderer(static_url=static_url)
        return [(u.email, component.Component(UserManager.get_app_user(u.username, data=u)).render(h, "search").write_htmlstring())
                for u in self.autocomplete_method(value)]


class AddMembers(object):

    def __init__(self, autocomplete_method):
        self.text_id = 'add_members_' + str(random.randint(10000000, 99999999))
        self.autocomplete = component.Component(
            autocomplete.Autocomplete(self.text_id, self.autocompletion, delimiter=','))
        self.autocomplete_method = autocomplete_method

    def autocompletion(self, value, static_url):
        h = xhtml.Renderer(static_url=static_url)
        return [(u.email, component.Component(UserManager.get_app_user(u.username, data=u)).render(h, "search").write_htmlstring()) for u in self.autocomplete_method(value)]
