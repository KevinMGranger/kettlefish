#    kettlefish is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    kettlefish is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with kettlefish.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function
import datetime
import json
import re

from twisted.words.protocols.irc import IRCClient
from twisted.internet.protocol import ReconnectingClientFactory
from twisted.internet import reactor

from kettlefish import translate_remyspeak


class KettleBot(IRCClient):
    bot_name = "kettlefish"
    channel = "#rit-foss"
    versionNum = 1
    sourceURL = "http://github.com/FOSSRIT/kettlefish"
    lineRate = 1

    def __init__(self, *args, **kwargs):
        with open('victims.json') as jfile:
            self.victims = json.load(jfile)

        self.quiet = None
        self.karma = re.compile(r'\+\+|--')
        self.xml = re.compile(r'<([\w]+)(?:\s[\w\s=\'"]*)?>')
        self.xml_close = re.compile(r'</([\w]+)(?:\s[\w\s=\'"]*)?>')

    def signedOn(self):
        """Called when bot has succesfully signed on to server."""
        self.join(self.factory.channel)
        self.factory.add_bot(self)

    def joined(self, channel):
        """This will get called when the bot joins the channel."""
        print("Joined %s" % channel)

    def can_talk(self, channel, message):
        if self.quiet and self.quiet > datetime.datetime.now():
            return None
        else:
            self.quiet = None
            self.msg(channel, message)

    def left(self, channel):
        """This will get called when the bot leaves the channel."""
        print("Left %s" % channel)

    def privmsg(self, user, channel, msg):
        """This will get called when the bot receives a message."""
        user = user.split('!', 1)[0]

        # Regexes to handle non-kettlefish actions
        shushify = re.match('{}: (un)?shush(.*)'.format(self.nickname), msg)
        optional = re.match('{}: opt (in|out)$'.format(self.nickname), msg)
        thanks = re.search('({0}.*thanks)|(thanks.*{0})'.format(self.nickname), msg)
        tag_list = self.xml.findall(msg.lower())
        untag_list = self.xml_close.findall(msg.lower())

        # Anything PM-ed to kettlefish will be translated
        if channel == self.nickname:
            self.msg(user, translate_remyspeak(msg))

        # Handle being told to shush or unshush
        elif shushify:
            args = shushify.groups()
            # This tests the existence of the 'un-' prefix
            if args[0] == 'un':
                self.quiet = None
                self.msg(channel, 'universal translation matrix re-enabled')
            else:
                m = 5
                if args[1]:
                    try:
                        # Don't shush longer than 90 minutes
                        m = min(int(args[2]), 90)
                    except ValueError:
                        pass
                self.quiet = datetime.datetime.now() + datetime.timedelta(minutes=m)
                self.msg(channel, 'quiet time')

        # I provide a valuable service to the community!
        elif thanks:
            self.can_talk(channel, "{}: You're welcome!".format(user))

        # But not that valuable...
        elif optional:
            if optional.groups()[0] == 'out':
                try:
                    self.victims.remove(user)
                except ValueError:
                    pass
            elif optional.groups()[0] == 'in':
                self.victims.append(user)
            with open('victims.json', 'w') as jfile:
                json.dump(self.victims, jfile)

        elif tag_list:
            for tag in untag_list:
                if tag in tag_list:
                    tag_list.remove(tag)
            if tag_list:
                response = ''.join('</' + tag + '>' for tag in tag_list[::-1])
                self.can_talk(channel, response)

        elif user in self.victims:
            translated = translate_remyspeak(msg)
            display = self.karma.sub('', translated)
            if not msg.lower() == translated.lower():
                self.can_talk(channel, 'What {} means is: {}'.format(user, display))

    def action(self, user, channel, msg):
        if user == 'decause' and msg == '&':
            self.can_talk(channel, '{} steps into the background'.format(user))


class KettleBotFactory(ReconnectingClientFactory):
    active_bot = None

    def __init__(self, protocol=KettleBot):
        self.protocol = protocol
        self.channel = protocol.channel
        IRCClient.nickname = protocol.bot_name
        IRCClient.realname = protocol.bot_name

    def add_bot(self, bot):
        self.active_bot = bot


if __name__ == '__main__':
    # create factory protocol and application
    f = KettleBotFactory()

    # connect factory to this host and port
    reactor.connectTCP("irc.freenode.net", 6667, f)

    # run bot
    reactor.run()
