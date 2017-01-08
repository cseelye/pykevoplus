#!/usr/bin/env python2.7
"""
This module provides convenient wrappers for controlling Kwikset Kevo locks
"""

from bs4 import BeautifulSoup
import functools
import json
import requests
import time

class KevoError(Exception):
    """Base exception for all Kevo errors"""
    pass

class Kevo(object):
    """
    Common mykevo.com operations
    """

    KEVO_URL_BASE = "https://mykevo.com"
    COMMANDS_URL_BASE = KEVO_URL_BASE + "/user/remote_locks/command"

    START_URL = KEVO_URL_BASE + "/login"
    LOGIN_URL = KEVO_URL_BASE + "/signin"

    @staticmethod
    def GetAuthToken(session):
        """
        Get a mykevo.com auth token from a logged-in session

        Args:
            session:    the session to use (requests.Session)

        Returns:
            An auth token (str)
        """
        token = None
        result = session.get(Kevo.START_URL)
        login_page = BeautifulSoup(result.text, "html.parser")
        for field in login_page.find_all("input"):
            if field.get("name") == "authenticity_token":
                token = field.get("value")
                break
        if not token:
            raise KevoError("Could not find auth token on signin page")
        return token

    @staticmethod
    def Login(session, username, password):
        """
        Login a session to mykevo.com

        Args:
            session:    the session to use (requests.Session)
            username:   your mykevo.com username (str)
            password:   your mykevo.com password (str)
        """
        token = Kevo.GetAuthToken(session)
        login_payload = {
            "user[username]" : username,
            "user[password]" : password,
            "authenticity_token" : token
        }
        result = session.post(Kevo.LOGIN_URL, login_payload)
#        print result.status_code
#        print result.text
        return result

    @staticmethod
    def GetLocks(username, password):
        """
        Get a list of Kevo locks in a mykevo.com account

        Args:
            username:   your mykevo.com username (str)
            password:   your mykevo.com password (str)

        Returns:
            A list of locks (list of KevoLock)
        """
        locks = []
        with requests.Session() as session:
            result = Kevo.Login(session, username, password)
            lock_page = BeautifulSoup(result.text, "html.parser")
            for lock in lock_page.find_all("ul", "lock"):
                lock_info = lock.find("div", class_="lock_unlock_container")
                lock_id = lock_info.get("data-lock-id")
                lock_detail_url = Kevo.COMMANDS_URL_BASE + "/lock.json?arguments={}".format(lock_id)
                detail_result = session.get(lock_detail_url)
                lock_details = json.loads(detail_result.text)
                locks.append(KevoLock.FromJSON(lock_details, username, password))
        return locks

def _manage_session(method):
    """ 
    Decorator to handle the HTTP session to mykevo.com
    This allows methods in KevoLock to not have to manage auth sessions themselves
    """
    @functools.wraps(method)
    def _wrapped(self, *args, **kwargs):
        close_session = False
        if not self.session:
            self.session = requests.Session()
            Kevo.Login(self.session, self.username, self.password)
            close_session = True
        try:
            return method(self, *args, **kwargs)
        finally:
            if self.session and close_session:
                self.session.close()
                self.session = None
    return _wrapped

class KevoLock(object):
    """
    Object to represent a Kwikset Kevo lock
    """

    @staticmethod
    def FromLockID(lockID, username, password):
        """
        Create a KevoLock from the ID of the lock

        Args:
            lockID:     the UUID of the lock (str)
            username:   your mykevo.com username (str)
            password:   your mykevo.com password (str)

        Returns:
            A ready to use lock object (KevoLock)
        """
        lock = KevoLock()
        lock.lockID = lockID
        lock.username = username
        lock.password = password
        lock.Refresh()
        return lock

    @staticmethod
    def FromJSON(lockJSON, username, password):
        """
        Create a KevoLock from the JSON metadata of the lock

        Args:
            lockJSON:   the JSON data of the lock (dict)
            username:   your mykevo.com username (str)
            password:   your mykevo.com password (str)

        Returns:
            A ready to use lock object (KevoLock)
        """
        lock = KevoLock()
        lock.username = username
        lock.password = password
        lock.data = lockJSON
        lock.lockID = lock.data["id"]
        lock.name = lock.data["name"]
        lock.state = lock.data["bolt_state"]
        return lock


    def __init__(self):
        """
        FromLockID factory constructor should be used instead of directly instantiating a KevoLock object
        """
        self.data = None
        self.lockID = None
        self.name = None
        self.password = None
        self.session = None
        self.state = None
        self.username = None

    def __str__(self):
        return "{}: {}".format(self.name, self.state)

    def __repr__(self):
        return "KevoLock(name={}, id={}, state={})".format(self.name, self.lockID, self.state)


    @_manage_session
    def _WaitForState(self, state, timeout=20):
        """
        Internal function to wait for the lock to achieve a given bolt state

        Args:
            state:      the bolt state to wait for (str)
            timeout:    how long to wait before giving up, in seconds (int)
        """
        start_time = time.time()
        while True:
            self.Refresh()
            if self.data["bolt_state"].lower() == state.lower():
                break
            if time.time() - start_time > timeout:
                raise KevoError("Timeout waiting for {}".format(state.lower()))
            time.sleep(1)

    def StartSession(self):
        """
        Start an auth session for this lock, so that multiple commands can be executed without re-authorizing each command
        """
        self.session = requests.Session()
        Kevo.Login(self.session, self.username, self.password)

    def EndSession(self):
        """
        Finish an auth session for this lock, so that any further commands will re-authorize
        """
        if self.session:
            self.session.close()
            self.session = None

    @_manage_session
    def Refresh(self):
        """
        Refresh the internal state of this lock object with the state from the real lock
        """
        lock_info_url = Kevo.COMMANDS_URL_BASE + "/lock.json?arguments={}".format(self.lockID)
        info_result = self.session.get(lock_info_url)
        if info_result.status_code != 200:
            raise KevoError("Error getting lock info: {}".format(info_result.text))
        self.data = json.loads(info_result.text)
        self.name = self.data["name"]
        self.state = self.data["bolt_state"]

    def WaitForLocked(self, timeout=20):
        """
        Wait or this lock to be in the locked bolt state

        Args:
            timeout:    how long to wait before giving up, in seconds (int)
        """
        self._WaitForState("locked", timeout)

    def WaitForUnlocked(self, timeout=20):
        """
        Wait or this lock to be in the unlocked bolt state

        Args:
            timeout:    how long to wait before giving up, in seconds (int)
        """
        self._WaitForState("unlocked", timeout)

    @_manage_session
    def Lock(self):
        """
        Lock this lock.  If the lock is already locked, this method has no effect.
        """
        command_url = Kevo.COMMANDS_URL_BASE + "/remote_lock.json?arguments={}".format(self.lockID)
        self.session.get(command_url)
        self.WaitForLocked()

    @_manage_session
    def Unlock(self):
        """
        Unlock this lock.  If the lock is already unlocked, this method has no effect.
        """
        command_url = Kevo.COMMANDS_URL_BASE + "/remote_unlock.json?arguments={}".format(self.lockID)
        self.session.get(command_url)
        self.WaitForUnlocked()

    @_manage_session
    def GetBoltState(self):
        """
        Retrieve the current bolt state of this lock

        Returns:
            The bolt state (str)
        """
        self.Refresh()
        return self.data["bolt_state"]

    def IsLocked(self):
        """
        Determine if this lock's bolt state is locked

        Returns:
            True if locked, false otherwise (bool)
        """
        return self.GetBoltState().lower() == "locked"

    def IsUnlocked(self):
        """
        Determine if this lock's bolt state is unlocked

        Returns:
            True if unlocked, false otherwise (bool)
        """
        return self.GetBoltState().lower() == "unlocked"


class KevoLockSession(object):
    """
    Context manager for kevo auth sessions
    """

    def __init__(self, kevoLock):
        self.lock = kevoLock

    def __enter__(self):
        self.lock.StartSession()

    def __exit__(self, *exc):
        self.lock.EndSession()


if __name__ == "__main__":
    from getpass import getpass

    user = raw_input("Username: ")
    passwd = getpass("Password: ")

    # Scrape the mykevo.com site to find the locks
    for kevolock in Kevo.GetLocks(user, passwd):
        print repr(kevolock)

    # Instantiate locks from IDs
    # Get the lock IDs by logging into mykevo.com, click Details for the lock, click Settings, the lock ID is on the right
#    front_door_id = "cca7cd1d-c1d5-43ce-a087-c73b974b3529"
#    back_door_id = "c60130cd-8139-4688-8ba3-199276a65ad6"
#    for lock_id in [front_door_id, back_door_id]:
#        kevolock = KevoLock.FromLockID(lock_id, user, passwd)
#        print str(kevolock)

    # Do multiple operations on a lock using a single session
#    kevolock = KevoLock.FromLockID(garage_door_id, user, passwd)
#    with KevoLockSession(kevolock):
#        kevolock.Unlock()
#        kevolock.Lock()

