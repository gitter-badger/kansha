# -*- coding:utf-8 -*-
#--
# Copyright (c) 2012-2014 Net-ng.
# All rights reserved.
#
# This software is licensed under the BSD License, as described in
# the file LICENSE.txt, which you should have received as part of
# this distribution.
#--
from kansha import validator
from kansha.services.components_repository import CardExtension


class CardDescription(CardExtension):
    """Description component,

    This component can be used for with all element which have a description
    field.
    Examples are available in card and board modules
    """

    LOAD_PRIORITY = 20

    def __init__(self, parent):
        """Initialization

        In:
            - ``parent`` -- the object parent
        """
        self.parent = parent
        self.text = parent.get_description()

    def change_text(self, text):
        """Edit the description

        In:
            - ``text`` -- the text of the description
        """
        # historically, canceling the description edition calls this function with None.
        # FIXME: that should not happen.
        if text is None:
            return
        text = text.strip()
        if text:
            text = validator.clean_html(text)
        self.text = text
        self.parent.set_description(text)

    def __nonzero__(self):
        """Return False if the description if empty
        """
        return bool(self.text)
