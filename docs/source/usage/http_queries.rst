HTTP queries
############

Several of Shyft's endpoints, such as `/source_files`, `/view_activities`, etc, allow you to specify the activities to
be acted upon by a HTTP GET query in a common format. That format is as follows::

    from_date=<date>&to_date=<date>&prototype=<integer>&type=<string>&id=<integer>,<integer>,<integer>,[...]

Note that `/delete` works in the same way, but the query (in the same format) is sent as a POST request, not a GET request.

As you can see, the possible parameters are:

* `from_date`: A date specified as a string in the `ISO 8601 <https://en.wikipedia.org/wiki/ISO_8601>`_ format. Only
  activities that began on or after this date will be returned.
  
* `to_date`: A date specified as a string in the ISO 8601 format. Only activities that began on or before this
  date will be returned.
  
* `prototype`: An integer, representing an activity ID. Only activities whose [prototype activity](/docs/matching)
  is the specified activity will be returned.
  
* `type`: A string, which should be one of the activity types recognised by Shyft (`run`, `walk`, etc). Only activities
  of the relevant type will be returned.
  
* `id`: A comma-separated list of integers. Only activities with an ID in the given list will be returned.