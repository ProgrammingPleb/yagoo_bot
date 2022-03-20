from typing import Optional, Union, TypedDict, List

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
    """
    def __init__(self,
                 channelID: str,
                 channelName: str):
        self.channelID = channelID
        self.channelName = channelName

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

class SubscriptionResponse():
    """
    Returned when a response for a subscription command was given.
    
    Attributes
    ---
    status: Whether the command was successfully finished or not.
    subTypes: The subscription types that the user requested.
    channelNames: A `list` containing all the names of the channels to be subscribed to.
    
    Additonal Initialization Arguments
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

class FandomChannel():
    def __init__(self, success: bool = False,
                 channelID: Optional[str] = None,
                 channelName: Optional[str] = None):
        self.success = success
        self.channelID = channelID
        self.channelName = channelName
