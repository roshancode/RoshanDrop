#!/usr/bin/env python
# Copyright (C) 2019 Roshan Lamichhane

import os
import time
from git import *
#import git

import log


class FSWatcher:
    def __init__(self, config):
        self._logger = log.Logger()
        self._config = config
        self._running = True
        self._checking = True
        self._syncFolder = None

        if not self._config.get_option('syncInterval', 'general'):
            self._config.set_option('syncInterval', 10, 'general')

        self._interval = self._config.get_option('syncInterval', 'general')

        # Init the local repository
        self.initRepository()

    def get_running(self):
        return self._running

    running = property(get_running)

    def get_checking(self):
        return self._checking

    checking = property(get_checking)

    def initRepository(self):
        # Check if a sync folder is specified
        self._syncFolder = self._config.get_option('syncFolder', 'general')
        if not self._syncFolder:
            # If no sync folder is specified, set it to the default
            homeDir = os.getenv("HOME")
            syncFolder = os.path.join(homeDir, 'RoshanDrop')
            self._config.set_option('syncFolder', syncFolder, 'general')
            self._config.write()
            self._syncFolder = syncFolder

        self._logger.info("Shares: " + self._syncFolder)

        # Check if the synchronization folder exits
        if not os.path.exists(self._syncFolder):
            os.mkdir(self._syncFolder)

        # Check if the user has already a GIT repository. If not, create one.
        os.chdir(self._syncFolder)
        if not os.path.exists(".git"):
            self._logger.info("Creating a new Git repository")
            self._repo = Repo.init(".", bare=False)
            assert self._repo.bare == False

            self._logger.info("Adding remote to Git repository")
            self._git = Git('.')

            # Define remote repository shorthand
            remote_rep_url = self._config.get_option('remoteUser', 'repository') + "@" + self._config.get_option('remoteHost', 'repository') + ":" + self._config.get_option('remoteRepositoryPath', 'repository')
            self._git_remote = self._repo.create_remote('origin', remote_rep_url)
        else:
            self._logger.info("Opening existing Git repository")
            self._repo = Repo(".")
            self._git = Git('.')

            remotes = self._repo.remotes
            self._git_remote = remotes[0]

    def get_updateInterval(self):
        return self._interval

    def set_updateInterval(self, value):
        self._interval = value;

    # The update interval for checking the file system for changes
    updateInterval = property(get_updateInterval, set_updateInterval)

    def watch(self):
        remote_check = True
        cleanup_counter = 0

        os.chdir(self._syncFolder)

        while self._running:
            if self._checking:
                # Check the remote repository
                if remote_check:
                    self._logger.info("Start checking remote repository")

                    try:
                        remote_head = self._git.ls_remote('origin', 'HEAD')

                        if remote_head:
                            remote_head = remote_head.split('\t')[0]
                            self._logger.debug("Remote head: " + remote_head)

                        try:
                            local_head = self._git.rev_parse('HEAD')
                            self._logger.debug("Local head: " + local_head)
                        except:
                            local_head = ''

                        if remote_head != local_head:
                            self._logger.info("Updating from remote repository...")
                            self._git.reset('--hard', 'HEAD')
                            self._git.pull('origin', 'master')
                            self._logger.info("Update from remote repository finished.")
                        else:
                            self._logger.info("Remote and local repository are in sync.")
                    except:
                        self._logger.info("Error checking remote repository!")

                    remote_check = False
                    self._logger.info("End checking remote repository")
                else:
                    remote_check = True

                # Checking local folder
                self._logger.info("Start checking local folder")

                add_count = 0
                change_count = 0

                # Check for added, untracked, modified and deleted files
                index = self._repo.index
                untracked_files = self._repo.untracked_files
                wdiff = index.diff(None)

                # Added files
                for diff_added in wdiff.iter_change_type('A'):
                    self._logger.info("Added: " + diff_added.a_blob.name)
                    change_count += 1

                # Modified files
                for diff_modified in wdiff.iter_change_type('M'):
                    self._logger.info("Modified: " + diff_modified.a_blob.name)
                    change_count += 1

                # Deleted files
                for diff_deleted in wdiff.iter_change_type('D'):
                    self._logger.info("Deleted: " + diff_deleted.a_blob.name)
                    change_count += 1

                # Untracked files
                for file in untracked_files:
                    self._logger.info("Untracked: " + file)
                    add_count += 1
                    change_count += 1

                # Add untracked files to the repository
                if add_count > 0:
                    self._logger.info("Adding " + str(add_count) + " new file(s)")
                    index.add(untracked_files)
                    #for newFile in untracked_files:
                    #    self._git.add(newFile)


                # Commit all changes
                if change_count > 0:
                    self._logger.info(str(change_count) + " file(s) changed. Start comitting...")
                    commit_message = "'" + str(change_count) + " file(s) updated" + "'"
                    try:
                        self._git.commit('-a', '-m', commit_message)
                    except:
                        self._logger.info("Warning: Commit failed!")

                    #if index.commit(str(change_count) + " file(s) updated"):
                    #   self._logger.info("All files are comitted.")
                    #else:
                    #   self._logger.info("Error committing files!")

                # If any changes; push it to the remote repository
                if change_count == 0 and add_count == 0:
                    self._logger.info("No changes")
                else:
                    self._logger.info("Pushing all changes to the remote repository...")
                    try:
                        self._git.push('origin', 'master')
                    except:
                        self._logger.info("Warning: GIT push failed!")
                    self._logger.info("Git push finished")

                    # Git repository cleanup
                    if cleanup_counter > 10:
                        self._logger.info("Cleaning up GIT repository")
                        self._git.gc('--auto')
                        cleanup_counter = 0
                        self._logger.info("Cleaning finished")
                    else:
                        cleanup_counter += 1

                self._logger.info("End checking local folder")

            # Sleep for the given time
            time.sleep(self._interval)

    def start(self):
        """
        Starts watching the repository.
        """
        self._checking = True

    def stop(self):
        """
        Stops watching the repository
        """
        self._checking = False
