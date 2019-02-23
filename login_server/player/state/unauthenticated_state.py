#!/usr/bin/env python3
#
# Copyright (C) 2018  Maurice van der Pot <griffon26@kfk4ever.com>,
# Copyright (C) 2018 Timo Pomer <timopomer@gmail.com>
#
# This file is part of taserver
#
# taserver is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# taserver is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with taserver.  If not, see <http://www.gnu.org/licenses/>.
#

from common.datatypes import *
from common.game_items import get_unmodded_class_menu_data
from .authenticated_state import AuthenticatedState
from ..state.player_state import PlayerState, handles


def choose_display_name(login_name, registered, names_in_use, max_name_length):
    if registered:
        display_name = login_name[:max_name_length]
    else:
        prefix = 'unvrf-'
        display_name = prefix + login_name[:max_name_length - len(prefix)]
        index = 2
        while display_name in names_in_use:
            display_name = 'unv%02d-%s' % (index, login_name[:max_name_length - len(prefix)])
            index += 1
            assert index < 100

    return display_name


class UnauthenticatedState(PlayerState):
    @handles(packet=a01bc)
    def handle_a01bc(self, request):
        self.player.send(a01bc())
        self.player.send(a0197())

    @handles(packet=a0033)
    def handle_a0033(self, request):
        self.player.send(a0033())

    @handles(packet=a003a)
    def handle_login_request(self, request):
        if request.findbytype(m0056) is None:  # request for login
            self.player.send(a003a())

        else:  # actual login
            self.player.login_name = request.findbytype(m0494).value
            self.player.password_hash = request.findbytype(m0056).content
            accounts = self.player.login_server.accounts

            validation_failure = self.player.login_server.validate_username(self.player.login_name)
            if validation_failure:
                self.player.send([
                    a003d().set([
                        m0442().set_success(False),
                        m02fc().set(STDMSG_LOGIN_INFO_INVALID),
                        m0219(),
                        m0019(),
                        m0623(),
                        m05d6(),
                        m03e3(),
                        m00ba()
                    ])
                ])
                self.logger.info("Rejected login attempt with user name %s: %s" %
                                 (self.player.login_name.encode('latin1'), validation_failure))

            else:
                if (self.player.login_name in accounts and
                        self.player.password_hash == accounts[self.player.login_name].password_hash):
                    self.player.login_server.change_player_unique_id(self.player.unique_id,
                                                                     accounts[self.player.login_name].unique_id)
                    self.player.registered = True

                names_in_use = [p.display_name for p in self.player.login_server.players.values()
                                if p.display_name is not None]
                self.player.display_name = choose_display_name(self.player.login_name,
                                                               self.player.registered,
                                                               names_in_use,
                                                               self.player.max_name_length)
                self.player.load()
                self.player.send([
                    a003d()
                        .set_menu_data(get_unmodded_class_menu_data())
                        .set_player(self.player),
                    m0662().set_original_bytes(0x8898, 0xdaff),
                    m0633().set_original_bytes(0xdaff, 0x19116),
                    m063e().set_original_bytes(0x19116, 0x1c6ee),
                    m067e().set_original_bytes(0x1c6ee, 0x1ec45),
                    m0442().set_success(True),
                    m02fc().set(STDMSG_LOGIN_IS_VALID),
                    m0219(),
                    m0019(),
                    m0623(),
                    m05d6(),
                    m00ba()
                ])
                self.player.set_state(AuthenticatedState)
