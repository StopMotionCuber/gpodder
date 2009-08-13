# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2009 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

"""Public developer API for gPodder

This module provides a nicely documented API for developers to
integrate podcast functionality into their applications.
"""

import gpodder
from gpodder import util
from gpodder import opml
from gpodder.libpodcasts import PodcastChannel
from gpodder.libgpodder import db
from gpodder.libgpodder import gl
from gpodder import download
from gpodder import console

class Podcast(object):
    """API interface of gPodder podcasts

    This is the API specification of podcast objects that
    are returned from API functions.

    Public attributes:
      title
      url
    """
    def __init__(self, _podcast):
        """For internal use only."""
        self._podcast = _podcast
        self.title = self._podcast.title
        self.url = self._podcast.url

    def get_episodes(self):
        """Get all episodes that belong to this podcast

        Returns a list of Episode objects that belong to this podcast."""
        return [Episode(e) for e in self._podcast.get_all_episodes()]

    def rename(self, title):
        """Set a new title for this podcast

        Sets a new title for this podcast that will be available
        as the "title" attribute of this object."""
        self._podcast.set_custom_title(title)
        self.title = self._podcast.title
        self._podcast.save()

    def delete(self):
        """Remove this podcast from the subscription list

        Removes the subscription and all downloaded episodes.
        """
        self._podcast.remove_downloaded()
        self._podcast.delete()
        self._podcast = None

    def update(self):
        """Updates this podcast by downloading the feed

        Downloads the podcast feed (using the feed cache), and
        adds new episodes and updated information to the database.
        """
        self._podcast.update(gl.config.max_episodes_per_feed)



class Episode(object):
    """API interface of gPodder episodes

    This is the API specification of episode objects that
    are returned from API functions.

    Public attributes:
      title
      url
      is_new
      is_downloaded
      is_deleted
    """
    def __init__(self, _episode):
        """For internal use only."""
        self._episode = _episode
        self.title = self._episode.title
        self.url = self._episode.url
        self.is_new = (self._episode.state == gpodder.STATE_NORMAL and \
                not self._episode.is_played)
        self.is_downloaded = (self._episode.state == gpodder.STATE_DOWNLOADED)
        self.is_deleted = (self._episode.state == gpodder.STATE_DELETED)

    def download(self):
        """Downloads the episode to a local file

        This will run the download in the same thread, so be sure
        to call this method from a worker thread in case you have
        a GUI running as a frontend."""
        task = download.DownloadTask(self._episode)
        task.status = download.DownloadTask.QUEUED
        task.run()


def get_podcasts():
    """Get a list of Podcast objects

    Returns all the subscribed podcasts from gPodder.
    """
    return [Podcast(p) for p in PodcastChannel.load_from_db(db, gl.config.download_dir)]

def get_podcast(url):
    """Get a specific podcast by URL

    Returns a podcast object for the URL or None if
    the podcast has not been subscribed to.
    """
    url = util.normalize_feed_url(url)
    channel = PodcastChannel.load(db, url, create=False, download_dir=gl.config.download_dir)
    if channel is None:
        return None
    else:
        return Podcast(channel)

def create_podcast(url, title=None):
    """Subscribe to a new podcast

    Add a subscription for "url", optionally
    renaming the podcast to "title" and return
    the resulting object.
    """
    url = util.normalize_feed_url(url)
    podcast = PodcastChannel.load(db, url, create=True, max_episodes=gl.config.max_episodes_per_feed, download_dir=gl.config.download_dir)
    if podcast is not None:
        if title is not None:
            podcast.set_custom_title(title)
        podcast.save()
        return Podcast(podcast)

    return None

def synchronize_device():
    """Synchronize episodes to a device

    WARNING: API subject to change.
    """
    console.synchronize_device(db, gl.config)


def finish():
    """Persist changed data to the database file

    This has to be called from the API user after
    data-changing actions have been carried out.
    """
    podcasts = PodcastChannel.load_from_db(db, gl.config.download_dir)
    exporter = opml.Exporter(gpodder.subscription_file)
    exporter.write(podcasts)
    db.commit()
    return True


