# GET queries

[NOTE: The below GET query system isn't yet implemented.]

Several of Shyft's endpoints, such as `/delete`, `/view_activities`, etc, allow you to specify the activities to be
acted upon by a GET query in a common format. That format is as follows:

`?from=<date_time>&to=<date_time>&prototype=<integer>&type=<string>&id=<integer>,<integer>,<integer>,[...]`

As you can see, the possible parameters are:

- `from`: A date and time, specified as a string in the [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) format. Only
  activities that began on or after this date and time will be returned.
  
- `to`: A date and time, specified as a string in the ISO 8601 format. Only activities that began on or before this 
  date and time will be returned.
  
- `prototype`: An integer, representing an activity ID. Only activities whose [prototype activity](/user_docs/matching)
  is the specified activity will be returned.
  
- `type`: A string, which should be one of the activity types recognised by Shyft (`run`, `walk`, etc). Only activities 
  of the relevant type will be returned.
  
- `id`: A comma-separated list of integers. Only activities with an ID in the given list will be returned.