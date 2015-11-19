#-*- coding: utf-8 -*-
#--
# Copyright (c) 2012-2014 Net-ng.
# All rights reserved.
#
# This software is licensed under the BSD License, as described in
# the file LICENSE.txt, which you should have received as part of
# this distribution.
#--

#=-
# (C)opyright PagesJaunes 2011
#
# This is Pagesjaunes proprietary source code
# Any reproduction modification or use without prior written
# approval from PagesJaunes is strictly forbidden.
#=-
import random
import string
from nagare.database import session
from nagare import local, security
from kansha.board import comp as board, models as board_models
from kansha.user import usermanager
from kansha.security import SecurityManager
from kansha.services.dummyassetsmanager.dummyassetsmanager import DummyAssetsManager
from kansha.services.services_repository import ServicesRepository
from kansha.services.mail import DummyMailSender


def setup_db(metadata):
    """Setup the tables

    In:
        - ``metadata`` -- the metadata from models
    """
    metadata.create_all()


def teardown_db(metadata):
    """Drop the tables

    In:
        - ``metadata`` -- the metadata from models
    """
    metadata.drop_all()
    session.close()


def word(length=20):
    """Random string generator

    In:
        - ``length`` -- the length of the string
    """
    return u''.join(random.sample(string.ascii_letters, length))


def integer():
    """Random integer generator
    """
    return random.randint(1, 10000)


class DummySecurityManager(security.common.Rules):

    """
    Dummy Security Manager to be used in unit tests
    """

    def has_permission(self, user, perm, subject):
        return True


def set_dummy_context():
    """Set a dummy context for security permission checks
    """
    local.request = local.Thread()
    security.set_user(None)
    security.set_manager(DummySecurityManager())


def set_context(user=None):
    """ """
    local.request = local.Thread()
    security.set_user(user)
    security.set_manager(SecurityManager('somekey'))


def get_or_create_data_user(suffixe=''):
    '''Get test user for suffixe, or create if not exists'''
    user_test = usermanager.UserManager.get_by_username(
        u'usertest_%s' % suffixe)
    if not user_test:
        user_test = usermanager.UserManager().create_user(
            u'usertest_%s' % suffixe,
            u'password', u'User Test %s' % suffixe,
            u'user_test%s@net-ng.com' % suffixe)
        session.add(user_test)
    return user_test


def create_user(suffixe=''):
    """Create Test user
    """
    user_test = get_or_create_data_user(suffixe)
    return usermanager.UserManager.get_app_user(u'usertest_%s' % suffixe)


def create_services():
    'Service mockups for testing components'
    _services = ServicesRepository()
    _services.register('assets_manager', DummyAssetsManager())
    _services.register('mail_sender', DummyMailSender())
    return _services


def create_board():
    """Create boards with default columns and default cards
    """
    user_test = get_or_create_data_user()
    data_board = board_models.DataBoard.from_template(get_board_data(), user_test)
    session.add(data_board)
    session.flush()
    _services = create_services()
    return _services(board.Board, data_board.id, 'boards', '', '', None, {'activated': False, 'basedir': ''})

def get_board_data():
    return {
        'title': u'this is a board',
        'labels': [
            {'title': u'Green',
             'color': u'#00ff00'},
            {'title': u'Blue',
             'color': u'#0000ff'},
        ],
        'columns': [
            {'title': u'Todo',
             'cards': [
                 {'title': u'Get some milk',
                  'description': u'Grab a bottle of milk at the grocery store',
                  'comments': [u'Not goat milk this time!'],
                  'labels': ['Green']
                  },
                 {'title': u'Prepare luggage',
                  'due_date': '2015-12-20',
                  'checklists': [
                      {'title': u'Clothes',
                       'items': [
                           {'title': u'Jeans', 'done': False},
                           {'title': u'Shirt', 'done': True},
                           {'title': u'Tuxedo', 'done': False}
                       ]
                       }
                  ]
                  }
             ]
            },
            {'title': u'Done',
             'cards': [
                 {'title': u'Repair kitchen sink',
                  'labels': ['Blue']}
             ]
            }
        ]

    }