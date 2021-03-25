Route matching
##############

When you add a new activity, Shyft attempts to match it to existing activities with a similar route, so that you can
track your progress over time on the same route. The process for checking if two activities involve roughly the same
route is two-fold:

1.  First, compare some basic features of the route, such as its length and the average and standard deviation of its
    latitude and longitude points. We call this "loose matching".
  
2.  Second, if the routes loose match, then compare the latitude and longitude data more closely using a `dynamic time
    warping <https://en.wikipedia.org/wiki/Dynamic_time_warping>`_ algorithm. We call this "tight matching".
  
Because it can take a while (usually a few seconds) to compare two given activities, we don't compare every new activity
against every existing activity. Instead, we maintain a list of "prototype" activities against which we compare new
activities. If a new activity tight matches a prototype activity, it is considered to match that prototype and every
other activity that matches the same prototype. If a new activity does not match any existing prototype, it becomes a
prototype itself.

The following configuration options determine how similar two routes need to be before they are considered to "match":

* `match_center_threshold` determines how close the centres of the routes need to be for a loose match.
  
* `match_length_threshold` determines how similar the lengths of the routes need to be for a loose match.
  
* `tight_match_threshold` determines how low the "distance" between two routes (as determined by the DTW algorithm)
  needs to be for a tight match.
  
In each case, the number that is checked against the relevant threshold is normalised in several ways. It is probably
best not to think of the thresholds as having any intrinsic meaning; larger values mean that activities are more likely
to match, whereas lower values mean that matches are less likely.