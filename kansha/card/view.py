# -*- coding:utf-8 -*-
# --
# Copyright (c) 2012-2014 Net-ng.
# All rights reserved.
#
# This software is licensed under the BSD License, as described in
# the file LICENSE.txt, which you should have received as part of
# this distribution.
# --
import peak

from nagare import presentation, var, security, component, ajax
from nagare.i18n import _

from kansha.card.comp import CardWeightEditor

from .comp import Card, NewCard, CardTitle, CardMembers


@presentation.render_for(Card, 'no_dnd')
def render_card_no_dnd(self, h, comp, *args):
    """No DnD wrapping of the card"""
    h << comp.render(h.AsyncRenderer())
    return h.root


@presentation.render_for(Card, 'new')
def render_card_new(self, h, comp, *args):
    h << comp.becomes(self, None)
    h << h.script(
        "card = YAHOO.util.Dom.get(%s);"
        "list = YAHOO.util.Dom.getAncestorByClassName(card, 'list-body');"
        "list.scrollTop = card.offsetTop - list.offsetTop;" %
        ajax.py2js(self.id)
    )
    return h.root


@presentation.render_for(Card)
def render(self, h, comp, *args):
    """Render the card"""

    extensions = [extension for name, extension in self.card_extensions]

    card_id = h.generate_id()

    onclick = h.a.action(lambda: comp.answer(comp)).get('onclick').replace('return', "")
    if self.column.board.card_matches:
        c_class = 'card highlight' if self.id in self.column.board.card_matches else 'card hidden'
    else:
        c_class = 'card'
    with h.div(id=self.id, class_=c_class):
        with h.div(id=card_id, onclick=onclick):
            with h.div(class_='headers'):
                h << [extension.render(h, 'header') for extension in extensions]
            with h.div(class_='covers'):
                h << self.title.render(h, 'card-title')
                h << [extension.render(h, 'cover') for extension in extensions]
            with h.div(class_='card-footer'):
                h << [extension.render(h, 'badge') for extension in extensions]

    h << h.script(
        "YAHOO.kansha.reload_cards[%s]=function() {%s}""" % (
            ajax.py2js(self.id),
            h.a.action(ajax.Update()).get('onclick')
        )
    )
    if self.must_reload_search:
        self.reload_search()
        h << h.script('''$(window).trigger('reload_search');''')

    return h.root


@presentation.render_for(Card, model='readonly')
def render(self, h, comp, *args):
    """Render the card read-only"""
    with h.div(id=self.id, class_='card'):
        with h.div:
            h << {
                'onclick': "window.location.href=%s" % ajax.py2js(
                    '%s#id_%s' % (self.data.column.board.url, self.id)
                )
            }
            h << self.title.render(h, 'card-title')
            # FIXME: unify with main card view.
    return h.root


@presentation.render_for(Card, model='edit')
def render_card_edit(self, h, comp, *args):
    """Render card in edition mode"""
    # Test for delete card
    if self.data is None:
        return h.root
    # h << h.script('''YAHOO.kansha.app.hideOverlay();''')

    with h.div(class_='card-edit-form'):
        with h.div(class_='header'):
            self.title.on_answer(lambda v: self.title.call(model='edit' if not self.title.model else None))
            h << h.AsyncRenderer().div(self.title, component.Component(self.column, 'title'), class_="async-title")
        with h.div(class_='grid-2'):
            with h.div(class_='card-edition'):
                for name, extension in self.card_extensions:
                    h << h.div(extension.render(h.AsyncRenderer()), class_=name)
            with h.div(class_='card-actions'):
                with h.form:
                    h << comp.render(h, 'delete-action')
                    h << [extension.render(h.AsyncRenderer(), 'action') for __, extension in self.card_extensions]
    return h.root


@presentation.render_for(Card, 'delete-action')
def render_card_delete(self, h, comp, model):
    if security.has_permissions('edit', self) and not self.column.is_archive:
        close_func = ajax.js(
            'function (){%s;}' %
            h.a.action(comp.answer, 'delete').get('onclick')
        )
        h << h.button(
            h.i(class_='icon-bin'),
            _('Delete'),
            class_='btn delete',
            onclick=(
                "if (confirm(%(confirm_msg)s)) {"
                "   YAHOO.kansha.app.archiveCard(%(close_func)s, %(id)s, %(col_id)s, %(archive_col_id)s);"
                "   reload_columns();"
                "}"
                "return false" %
                {
                    'close_func': ajax.py2js(close_func),
                    'id': ajax.py2js(self.id),
                    'col_id': ajax.py2js(self.column.id),
                    'archive_col_id': ajax.py2js(
                        self.column.board.archive_column.id
                    ),
                    'confirm_msg': ajax.py2js(
                        _(u'This card will be deleted. Are you sure?')
                    ).decode('UTF-8')
                }
            )
        )
    return h.root


@presentation.render_for(Card, 'calendar')
def render(self, h, comp, *args):
    card = ajax.py2js(self, h)
    if card:
        clicked_cb = h.a.action(
            lambda: comp.answer(comp)
        ).get('onclick')

        dropped_cb = h.a.action(
            ajax.Update(
                action=self.card_dropped,
                render=lambda render: '',
                with_request=True
            )
        ).get('onclick')[:-2]

        h << h.script(u"""YAHOO.kansha.app.add_event($('#calendar'), %(card)s,
                         function() { %(clicked_cb)s},
                         function(start) { %(dropped_cb)s&start="+start);} )""" % {
            'card': card,
            'clicked_cb': clicked_cb,
            'dropped_cb': dropped_cb
        })
    return h.root


@presentation.render_for(Card, 'dnd')
def render_card_dnd(self, h, comp, *args):
    """DnD wrapping of the card"""
    if self.data is not None:
        id_ = h.generate_id('dnd')
        with h.div(id=id_):
            h << comp.render(h.AsyncRenderer())
            h << h.script('YAHOO.kansha.dnd.initCard(%s)' % ajax.py2js(id_))
    return h.root

########################


@presentation.render_for(CardWeightEditor, 'action')
def render_cardweighteditor(self, h, comp, *args):
    if self.target.weighting_on():
        h << self.action_button
    return h.root


@presentation.render_for(CardWeightEditor, 'action_button')
def render_cardweighteditor_button(self, h, comp, *args):
    h << h.a(h.i(class_='icon-star-full'), self.weight, class_='btn').action(
            comp.call, self, model='edit')
    return h.root


@presentation.render_for(CardWeightEditor, 'edit')
def render_cardweighteditor_edit(self, h, comp, *args):
    def answer():
        if self.commit():
            comp.answer()

    if self.board.weighting_cards == self.WEIGHTING_FREE:
        with h.form:
            h << h.input(value=self.weight(), type='text').action(self.weight).error(self.weight.error)
            h << h.button(_('Save'), class_='btn btn-primary').action(answer)

    elif self.board.weighting_cards == self.WEIGHTING_LIST:
        with h.form:
            with h.div(class_='btn select'):
                with h.select.action(self.weight):
                    for value in self.board.weights.split(','):
                        h << h.option(value, value=value).selected(self.weight)
            h << h.button(_('Save'), class_='btn btn-primary').action(answer)

    return h.root


@presentation.render_for(CardWeightEditor, 'badge')
def render_cardweighteditor_edit(self, h, comp, *args):
    if self.weight.value:
        with h.span(class_='badge'):
            label = _('weight')
            h << h.span(h.i(class_='icon-star-full'), ' ',
                        self.weight.value, class_='label',
                        data_tooltip=label)
    return h.root


### members handling

@presentation.render_for(CardMembers, 'action')
def render_card_members(self, h, comp, *args):
    """Member section view for card

    First members icons,
    Then icon "more user" if necessary
    And at the end icon "add user"
    """
    with h.div(class_='members'):
        h << h.script('''YAHOO.kansha.app.hideOverlay();''')
        for m in self.members[:self.max_shown_members]:
            h << m.on_answer(self.remove_member).render(h, model="overlay-remove")
        if len(self.members) > self.max_shown_members:
            h << h.div(self.see_all_members, class_='more')
        h << h.div(self.overlay_add_members, class_='add')
    return h.root


@presentation.render_for(CardMembers, 'badge')
def render_members_badge(self, h, comp, model):
    if security.has_permissions('edit', self.card):
        h << comp.render(h, 'action')
    else:
        h << comp.render(h, 'members_read_only')
    return h.root


@presentation.render_for(CardMembers, model='members_read_only')
def render_card_members_read_only(self, h, comp, *args):
    """Member section view for card

    First members icons,
    Then icon "more user" if necessary
    And at the end icon "add user"
    """
    with h.div(class_='members'):
        for m in self.members[:self.max_shown_members]:
            member = m.render(h, "avatar")
            member.attrib.update({'class': 'miniavatar unselectable'})
            h << member
        if len(self.members) > self.max_shown_members:
            h << h.div(self.see_all_members, class_='more')
    return h.root


@presentation.render_for(CardMembers, "members_list_overlay")
def render_members_members_list_overlay(self, h, comp, *args):
    """Overlay to list all members"""
    h << h.h2(_('All members'))
    with h.form:
        with h.div(class_="members"):
            if security.has_permissions('edit', self):
                h << [m.on_answer(comp.answer).render(h, "remove") for m in self.members]
            else:
                h << [m.render(h, "avatar") for m in self.members]
    return h.root


@presentation.render_for(CardMembers, "add_member_overlay")
def render_members_add_member_overlay(self, h, comp, *args):
    """Overlay to add member"""
    h << h.h2(_('Add members'))
    if self.favorites:
        with h.div(class_="favorites"):
            h << h.h3(_('Suggestions'))
            with h.ul:
                h << h.li(self.favorites)
    with h.div(class_="members search"):
        h << self.new_member
    return h.root


#####


@presentation.render_for(NewCard)
def render_new_card(self, h, comp, *args):
    """Render card creator minified"""
    h << h.a(h.strong('+'), h.span(_('Add a card')),
             class_='link-small').action(lambda: comp.answer(comp.call(model='add')))
    if self.needs_refresh:
        h << h.script('increase_version();')
        self.toggle_refresh()
    return h.root


@presentation.render_for(NewCard, 'add')
def render_new_card_add(self, h, comp, *args):
    """Render card creator form"""
    text = var.Var()
    id_ = h.generate_id('newCard')

    def answer():
        self.toggle_refresh()
        comp.answer(text())

    with h.form(class_='card-add-form'):
        h << h.input(type='text', id=id_).action(text)
        h << h.button(_('Add'), class_='btn btn-primary').action(answer)
        h << ' '
        h << h.button(_('Cancel'), class_='btn').action(comp.answer)

    h << h.script("""document.getElementById(%s).focus(); """ % ajax.py2js(id_))

    return h.root


@presentation.render_for(CardTitle, 'card-title')
def render_card_title(self, h, comp, *args):
    """Render the title of the associated card"""
    h << h.a(self.text)
    return h.root


@peak.rules.when(ajax.py2js, (Card,))
def py2js(value, h):
    due_date = ajax.py2js(value.due_date(), h)
    if due_date:
        return u'{title:%s, editable:true, allDay: true, start: %s}' % (
            ajax.py2js(value.get_title(), h).decode('utf-8'), due_date)
    else:
        return None
