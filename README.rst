==========
pykevoplus
==========

Python module for controlling Kwikset Kevo locks

Kwikset does not provide an official API for their Kevo locks; I reverse
engineered this module from the mykevo.com web app.

To use this module you will need to have a `Kevo Plus`_ installed and a
registered account on `mykevo.com`_. You will need your mykevo.com
credentials to use this module.

This module is published to `pypi`_ so you can install it simply via ``pip install pykevoplus``

Usage
=====

The ``Kevo.GetLocks()`` function will attempt to scrape the mykevo.com web
site to find your locks; as of this writing it can find all of your
locks, but scraping the HTML might break at any time if Kwikset changes
the website.

.. code:: python

    from pykevoplus import Kevo
    locks = Kevo.GetLocks("username@email.com", "password123")
    for lock in locks:
        print repr(lock)

Output::

    KevoLock(name=Front Door, id=cca7cd1d-c1d5-43ce-a087-c73b974b3529, state=Locked)
    KevoLock(name=Back Door, id=c60130cd-8139-4688-8ba3-199276a65ad6, state=Locked)

A better way is to explicitly instantiate a ``KevoLock`` object using the
UUID of the lock. You can get the lock IDs manually by logging into
mykevo.com, click Details for the lock, click Settings, the lock ID is
on the right.

.. code:: python

    from pykevoplus import KevoLock
    lock = KevoLock.FromLockID("cca7cd1d-c1d5-43ce-a087-c73b974b3529", "username@email.com", "password123")

Locking and Unlocking
'''''''''''''''''''''

.. code:: python

    from pykevoplus import KevoLock
    lock = KevoLock.FromLockID(lock_id, username, password)
    lock.Unlock()
    print lock.GetBoltState()
    lock.Lock()
    print lock.GetBoltState()

Output::

    Unlocked
    Locked

Multiple operations in the same session
'''''''''''''''''''''''''''''''''''''''

The ``KevoLockSession`` context manager allows you to perform multiple
operations on a lock with a single auth session

.. code:: python

    from pykevoplus import KevoLock, KevoLockSession
    lock = KevoLock.FromLockID(lock_id, username, password)
    with KevoLockSession(lock):
        lock.Unlock()
        lock.Lock()

Known Issues
============

* Error handling is extremely basic and needs much more work. Communication errors as well as lock bolt errors need to be addressed
* No unit tests yet
* Now supports Python 3.x



.. _Kevo Plus: http://www.kwikset.com/kevo/plus
.. _mykevo.com: mykevo.com
.. _pypi: https://pypi.python.org/pypi/pykevoplus

