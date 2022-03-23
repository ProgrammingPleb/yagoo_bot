import discord
from discord.ext import commands
from typing import Optional, Union, TypedDict, List
from yagoo.types.error import AccountNotFound, ChannelNotFound, InvalidSubscriptionType, NoArguments, NoFollows, NoSubscriptions

class SubscriptionList(TypedDict, total=False):
    livestream: bool
    milestone: bool
    premiere: bool
    twitter: bool

class YouTubeChannel():
    """
    Represents a YouTube channel.
    
    Attributes
    ---
    channelID: The channel's ID.
    channelName: The channel's name.
    twitter: The channel's Twitter account handle.
    """
    def __init__(self,
                 channelID: str,
                 channelName: str,
                 twitter: str = None):
        self.channelID = channelID
        self.channelName = channelName
        self.twitter = twitter

class TwitterAccount():
    """
    Represents a Twitter account.
    
    Attributes
    ---
    accountID: The account's ID.
    handle: The account's handle/username.
    name: The account's display name.
    """
    def __init__(self, accountID: str, handle: str, name: str):
        self.accountID = accountID
        self.handle = handle
        self.name = name

class SubscriptionData():
    """
    Returned when a `dict` of subscription types are given.
    
    Attributes
    ---
    subList: A `TypedDict` of the subscription types that was requested.
    """
    def __init__(self,
                 subList: Optional[SubscriptionList] = None):
        self.subList = subList

class ChannelSubscriptionData():
    """
    Returned when a channel subscription data is requested.
    
    Attributes
    ---
    exists: If any YouTube channels are being subscribed on the Discord channel.
    allChannels: A list of every YouTube channel being subscribed.
    subscriptions: A subscription type-seperated object with individual subscription types as a `list`.
    """
    class SubscriptionType():
        def __init__(self):
            self.livestream: List[YouTubeChannel] = []
            self.milestone: List[YouTubeChannel] = []
            self.premiere: List[YouTubeChannel] = []
            self.twitter: List[YouTubeChannel] = []
        
    def __init__(self, exists: bool = False):
        self.exists: bool = exists
        self.allChannels: list[YouTubeChannel] = []
        self.subscriptions = self.SubscriptionType()
        self._rawChannelID: List[str] = []
        self._rawChannelListing: dict = {}
    
    def addChannel(self,
                   subscriptionType: str,
                   channelID: str,
                   channelName: str,
                   twitter: str = None):
        """
        Add a YouTube channel that is subscribed to the Discord channel.
        
        Arguments
        ---
        subscriptionType: The channel subscription type.
        channelID: The YouTube channel's ID.
        channelName: The YouTube channel's name.
        twitter: The Twitter account associated with the YouTube channel. (Required if the subscription type is "twitter")
        """
        if channelID not in self._rawChannelID:
            self._rawChannelID.append(channelID)
            self._rawChannelListing[channelID] = YouTubeChannel(channelID, channelName, twitter)
            self.allChannels.append(YouTubeChannel(channelID, channelName))
        else:
            if twitter and not (self._rawChannelListing[channelID]).twitter:
                self._rawChannelListing[channelID] = YouTubeChannel(channelID, channelName, twitter)
                for channel in self.allChannels:
                    if channel.channelID == channelID:
                        self.allChannels.remove(channel)
                self.allChannels.append(YouTubeChannel(channelID, channelName, twitter))
        if subscriptionType == "livestream":
            self.subscriptions.livestream.append(YouTubeChannel(channelID, channelName))
        elif subscriptionType == "milestone":
            self.subscriptions.milestone.append(YouTubeChannel(channelID, channelName))
        elif subscriptionType == "premiere":
            self.subscriptions.premiere.append(YouTubeChannel(channelID, channelName))
        elif subscriptionType == "twitter":
            self.subscriptions.twitter.append(YouTubeChannel(channelID, channelName, twitter))
        else:
            raise InvalidSubscriptionType(subscriptionType)
    
    def findChannel(self, channelID: str) -> YouTubeChannel:
        """
        Finds a YouTube channel that the Discord channel is subscribed to.
        
        Arguments
        ---
        channelID: The channel ID corresponding to the YouTube channel.
        """
        if channelID in self._rawChannelListing.keys():
            return self._rawChannelListing[channelID]
        raise ChannelNotFound(channelID)
    
    def findTypes(self, channelID: str) -> List[str]:
        """
        Finds the subscription types of a certain channel.
        
        Arguments
        ---
        channelID: The channel ID corresponding to the YouTube channel.
        """
        if channelID in self._rawChannelListing.keys():
            subTypes = []
            channelSearch = self.findChannel(channelID)
            
            if channelSearch.twitter:
                subTypes.append("twitter")
            for channel in self.subscriptions.livestream:
                if channel.channelID == channelSearch.channelID:
                    subTypes.append("livestream")
            for channel in self.subscriptions.milestone:
                if channel.channelID == channelSearch.channelID:
                    subTypes.append("milestone")
            for channel in self.subscriptions.premiere:
                if channel.channelID == channelSearch.channelID:
                    subTypes.append("premiere")
            return subTypes
        raise ChannelNotFound(channelID)

class TwitterFollowData():
    """
    Returned when a channel's Twitter follows are requested.
    
    Attributes
    ---
    exists: If any Twitter accounts are being followed on the channel.
    accounts: A list of every Twitter accounts being followed.
    """
    def __init__(self, exists: bool = False):
        self.exists = exists
        self.accounts: List[TwitterAccount] = []
        self._rawAccountListing: dict = {}
    
    def addAccount(self, accountID: str, handle: str, name: str):
        """
        Adds an account to the Twitter follows data.
        
        Arguments
        ---
        accountID: The Twitter account's ID.
        name: The Twitter account's display name.
        """
        self.accounts.append(TwitterAccount(accountID, handle, name))
        self._rawAccountListing[accountID] = TwitterAccount(accountID, handle, name)
    
    def findAccount(self, accountID: str) -> TwitterAccount:
        """
        Finds the account by the Twitter account's handle/username.
        
        Arguments
        ---
        accountID: The Twitter account's ID.
        """
        if accountID in self._rawAccountListing.keys():
            return self._rawAccountListing[accountID]
        raise AccountNotFound(accountID)

class SubscriptionResponse():
    """
    Returned when a response for a subscription command is given.
    
    Attributes
    ---
    status: Whether the command was successfully finished or not.
    subTypes: The subscription types that the user requested.
    channelNames: A `list` containing all the names of the channels to be subscribed to.
    
    Additional Initialization Arguments
    ---
    channelIDs: The channel IDs of the channels to be subscribed to. Should not be used with `channelNames`.
    channelData: Channels data with `id` as the main key and the channel name as the data. Should not be used with `channelNames`.
    """
    def __init__(self,
                 status: bool,
                 subTypes: Optional[List[str]] = None,
                 channelIDs: Optional[List[str]] = None,
                 channelData: Optional[dict] = None,
                 channelNames: Optional[List[str]] = None):
        self.status = status
        self.subTypes = subTypes
        self.channelNames: List[str] = []
        if channelIDs and channelData:
            for channelID in channelIDs:
                self.channelNames.append(channelData[channelID])
        if channelNames:
            self.channelNames = channelNames

class UnsubscriptionResponse():
    """
    Returned when a response for an unsubscribe command is given.
    
    Attributes
    ---
    status: Whether the command was successfully finished or not.
    subTypes: The subscription types to be unsubscribed from
    """
    def __init__(self,
                 status: bool,
                 subTypes: Optional[List[str]] = None,
                 channels: Optional[List[YouTubeChannel]] = None):
        self.status = status
        self.subTypes = subTypes
        self.channels = channels

class CategorySubscriptionResponse():
    """
    Returned when a response for a category subscription was given.
    
    Attributes
    ---
    status: Whether the command was successfully finished or not.
    category: The name of the channel category.
    allInCategory: If the user wants to subscribe to all the channels in the category.
    channelIDs: The YouTube channel ID of the chosen channel, if the user chooses a channel.
    channelName: The YouTube channel name of the chosen channel, if the user chooses a channel.
    """
    def __init__(self,
                 status: bool,
                 category: Optional[str] = None,
                 allInCategory: Optional[bool] = False,
                 channelIDs: Optional[List[str]] = None,
                 channelData: Optional[dict] = None):
        self.status = status
        self.category = category
        self.allInCategory = allInCategory
        self.channels: List[YouTubeChannel] = []
        if channelIDs and channelData:
            for channelID in channelIDs:
                self.channels.append(YouTubeChannel(channelID, channelData[channelID]["name"]))
    
    def addChannel(self, channelID: str, channelName: str):
        """
        Adds a specific YouTube channel to the response.
        
        Useful if the channel is to be added after the class is first initialized.
        
        Arguments
        ---
        channelID: The ID of the YouTube channel.
        channelName: The name of the YouTube channel.
        """
        self.channel = YouTubeChannel(channelID, channelName)

class ChannelSearchResponse():
    """
    Returned after the Fandom scraper returns a search response for a channel.
    
    Attributes
    ---
    status: The status of the search. (status.matched, status.cannotMatch)
    channelName: The exact channel name in the wiki.
    searchResults: A `list` of other search results.
    """
    
    class SearchStatus():
        def __init__(self, matched: bool, cannotMatch: bool):
            self.matched = matched
            self.cannotMatch = cannotMatch
    
    def __init__(self, matched: bool = False, cannotMatch: bool = False, channelName: Optional[str] = None, searchResults: Optional[List[str]] = None):
        self.status = self.SearchStatus(matched, cannotMatch)
        self.channelName = channelName
        self.searchResults = searchResults
    
    def matched(self):
        """Sets the status to be in the "Matched" state."""
        self.status.matched = True
        self.status.cannotMatch = False
    
    def cannotMatch(self):
        """Sets the status to be in the "Cannot Match" state."""
        self.status.matched = False
        self.status.cannotMatch = True
    
    def failed(self):
        """Sets the status to be in the "Failed" state."""
        self.status.matched = False
        self.status.cannotMatch = False

class TwitterUnfollowResponse():
    """
    Returned when a Twitter unfollow response was given.
    
    Attributes
    ---
    status: Whether the command was successfully finished or not.
    allAccounts: If the user wants to unfollow all the accounts in the 
    accounts: The Twitter accounts to be unfollowed.
    """
    def __init__(self, status: bool = False, allAccounts: bool = False):
        self.status = status
        self.allAccounts = allAccounts
        self.accounts: List[TwitterAccount] = []
    
    def addAccount(self, accountID: str, handle: str, name: str):
        """
        Adds an account to the Twitter follows data.
        
        Arguments
        ---
        accountID: The Twitter account's ID.
        handle: The Twitter account's handle.
        name: The Twitter account's display name.
        """
        self.accounts.append(TwitterAccount(accountID, handle, name))
    
    def accountIDs(self):
        """
        Returns a list of Twitter account IDs to unfollow from.
        """
        result: List[str] = []
        
        for account in self.accounts:
            result.append(account.accountID)
        
        return result

class FandomChannel():
    def __init__(self, success: bool = False,
                 channelID: Optional[str] = None,
                 channelName: Optional[str] = None):
        self.success = success
        self.channelID = channelID
        self.channelName = channelName

class ErrorReport():
    def __init__(self,
                 cmd: Union[commands.Context, discord.Interaction],
                 error: Union[commands.errors.CommandInvokeError, discord.app_commands.CommandInvokeError]):
        self.cmd = cmd
        self.error = error
        self.report: str = None
        self.strErrors()
        self.yagooErrors()
        self.discordErrors()
    
    def strErrors(self):
        if "403 Forbidden" in str(self.error):
            if isinstance(self.cmd, commands.Context):
                user = self.cmd.author
            else:
                user = self.cmd.user
            
            permData = [{
                "formatName": "Manage Webhooks",
                "dataName": "manage_webhooks"
            }, {
                "formatName": "Manage Messages",
                "dataName": "manage_messages"
            }]
            permOutput = []
            for perm in iter(self.cmd.guild.permissions_for(user)):
                for pCheck in permData:
                    if perm[0] == pCheck["dataName"]:
                        if not perm[1]:
                            permOutput.append(pCheck["formatName"])
            plural = "this permission"
            if len(permOutput) > 1:
                plural = "these permissions"
            self.report = "This bot has insufficient permissions for this channel.\n" \
                         f"Please allow the bot {plural}:\n"
            for perm in permOutput:
                self.report += f'\n - `{perm}`'
        elif "No Twitter ID" in str(self.error):
            self.report = "There was no Twitter account link given!\n" \
                          "Ensure that the account's Twitter link or screen name is supplied to the command."
        elif "50 - User not found." in str(self.error):
            self.report = "This user was not found on Twitter!\n" \
                          "Make sure the spelling of the user's Twitter link/screen name is correct!"
    
    def yagooErrors(self):
        if isinstance(self.error.original, NoSubscriptions):
            self.report = "There are no subscriptions for this channel.\n" \
                          "Subscribe to a channel's notifications by using the `subscribe` command."
        elif isinstance(self.error.original, ChannelNotFound):
            self.report = "The YouTube channel is not subscribed to this Discord channel." \
                          "Subscribe to the channel's notifications by using the `subscribe` command."
        elif isinstance(self.error.original, NoFollows):
            self.report = "This channel is not following any Twitter accounts.\n" \
                          "Follow a Twitter account's tweets by using the `follow` command."
        elif isinstance(self.error.original, NoArguments):
            self.report = "A command argument was not given when required to."
    
    def discordErrors(self):
        if isinstance(self.error, (commands.CheckFailure, discord.app_commands.errors.CheckFailure)):
            self.report = "You are missing permissions to use this bot.\n" \
                          "Ensure that you have one of these permissions for the channel/server:\n\n" \
                          " - `Administrator (Server)`\n - `Manage Webhooks (Channel/Server)`"
        elif isinstance(self.error, discord.errors.Forbidden):
            self.report = "The bot is missing permissions for this server/channel!\n" \
                          "Ensure that you have set these permissions for the bot to work:\n\n" \
                          "- Manage Webhooks\n- Send Messages\n- Manage Messages"
