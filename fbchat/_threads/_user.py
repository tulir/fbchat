import attr
import datetime
from ._abc import ThreadABC
from .._common import log, attrs_default
from .. import _util, _session, _models

from typing import Optional


GENDERS = {
    # For standard requests
    0: "unknown",
    1: "female_singular",
    2: "male_singular",
    3: "female_singular_guess",
    4: "male_singular_guess",
    5: "mixed",
    6: "neuter_singular",
    7: "unknown_singular",
    8: "female_plural",
    9: "male_plural",
    10: "neuter_plural",
    11: "unknown_plural",
    # For graphql requests
    "UNKNOWN": "unknown",
    "FEMALE": "female_singular",
    "MALE": "male_singular",
    # '': 'female_singular_guess',
    # '': 'male_singular_guess',
    # '': 'mixed',
    "NEUTER": "neuter_singular",
    # '': 'unknown_singular',
    # '': 'female_plural',
    # '': 'male_plural',
    # '': 'neuter_plural',
    # '': 'unknown_plural',
}


@attrs_default
class User(ThreadABC):
    """Represents a Facebook user. Implements `ThreadABC`.

    Example:
        >>> user = fbchat.User(session=session, id="1234")
    """

    #: The session to use when making requests.
    session: _session.Session
    #: The user's unique identifier.
    id: str = attr.ib(converter=str)

    def _to_send_data(self):
        return {
            "other_user_fbid": self.id,
            # The entry below is to support .wave
            "specific_to_list[0]": "fbid:{}".format(self.id),
        }

    def _copy(self) -> "User":
        return User(session=self.session, id=self.id)

    async def confirm_friend_request(self):
        """Confirm a friend request, adding the user to your friend list.

        Example:
            >>> user.confirm_friend_request()
        """
        data = {"to_friend": self.id, "action": "confirm"}
        j = await self.session._payload_post("/ajax/add_friend/action.php?dpr=1", data)

    async def remove_friend(self):
        """Remove the user from the client's friend list.

        Example:
            >>> user.remove_friend()
        """
        data = {"uid": self.id}
        j = await self.session._payload_post("/ajax/profile/removefriendconfirm.php", data)

    async def block(self):
        """Block messages from the user.

        Example:
            >>> user.block()
        """
        data = {"fbid": self.id}
        j = await self.session._payload_post("/messaging/block_messages/?dpr=1", data)

    async def unblock(self):
        """Unblock a previously blocked user.

        Example:
            >>> user.unblock()
        """
        data = {"fbid": self.id}
        j = await self.session._payload_post("/messaging/unblock_messages/?dpr=1", data)


@attrs_default
class UserData(User):
    """Represents data about a Facebook user.

    Inherits `User`, and implements `ThreadABC`.
    """

    #: The user's picture
    photo: _models.Image
    #: The name of the user
    name: str
    #: Whether the user and the client are friends
    is_friend: bool
    #: The users first name
    first_name: str
    #: The users last name
    last_name: Optional[str] = None
    #: When the thread was last active / when the last message was sent
    last_active: Optional[datetime.datetime] = None
    #: Number of messages in the thread
    message_count: Optional[int] = None
    #: Set `Plan`
    plan: Optional[_models.PlanData] = None
    #: The profile URL. ``None`` for Messenger-only users
    url: Optional[str] = None
    #: The user's gender
    gender: Optional[str] = None
    #: From 0 to 1. How close the client is to the user
    affinity: Optional[float] = None
    #: The user's nickname
    nickname: Optional[str] = None
    #: The clients nickname, as seen by the user
    own_nickname: Optional[str] = None
    #: The message color
    color: Optional[str] = None
    #: The default emoji
    emoji: Optional[str] = None

    @staticmethod
    def _get_other_user(data):
        (user,) = (
            node["messaging_actor"]
            for node in data["all_participants"]["nodes"]
            if node["messaging_actor"]["id"] == data["thread_key"]["other_user_id"]
        )
        return user

    @classmethod
    def _from_graphql(cls, session, data):
        c_info = cls._parse_customization_info(data)

        plan = None
        if data.get("event_reminders") and data["event_reminders"].get("nodes"):
            plan = _models.PlanData._from_graphql(
                session, data["event_reminders"]["nodes"][0]
            )

        return cls(
            session=session,
            id=data["id"],
            url=data["url"],
            first_name=data["first_name"],
            last_name=data.get("last_name"),
            is_friend=data["is_viewer_friend"],
            gender=GENDERS.get(data["gender"]),
            affinity=data.get("viewer_affinity"),
            nickname=c_info.get("nickname"),
            color=c_info["color"],
            emoji=c_info["emoji"],
            own_nickname=c_info.get("own_nickname"),
            photo=_models.Image._from_uri(data["profile_picture"]),
            name=data["name"],
            message_count=data.get("messages_count"),
            plan=plan,
        )

    @classmethod
    def _from_thread_fetch(cls, session, data):
        user = cls._get_other_user(data)
        if user["__typename"] != "User":
            # TODO: Add Page._from_thread_fetch, and parse it there
            log.warning("Tried to parse %s as a user.", user["__typename"])
            return None

        c_info = cls._parse_customization_info(data)

        plan = None
        if data["event_reminders"]["nodes"]:
            plan = _models.PlanData._from_graphql(
                session, data["event_reminders"]["nodes"][0]
            )

        return cls(
            session=session,
            id=user["id"],
            url=user["url"],
            name=user["name"],
            first_name=user["short_name"],
            is_friend=user["is_viewer_friend"],
            gender=GENDERS.get(user["gender"]),
            nickname=c_info.get("nickname"),
            color=c_info["color"],
            emoji=c_info["emoji"],
            own_nickname=c_info.get("own_nickname"),
            photo=_models.Image._from_uri(user["big_image_src"]),
            message_count=data["messages_count"],
            last_active=_util.millis_to_datetime(int(data["updated_time_precise"])),
            plan=plan,
        )

    @classmethod
    def _from_all_fetch(cls, session, data):
        return cls(
            session=session,
            id=data["id"],
            first_name=data["firstName"],
            url=data["uri"],
            photo=_models.Image(url=data["thumbSrc"]),
            name=data["name"],
            is_friend=data["is_friend"],
            gender=GENDERS.get(data["gender"]),
        )
