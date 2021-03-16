# Route matching

When you add a new activity, Shyft attempts to match it to existing activities with a similar route, so that you can
track your progress over time on the same route. The process for checking if two activities involve roughly the same
route is two-fold:

- First, compare some basic features of the route, such as its length and the average and standard deviation of its
  latitude and longitude points. We call this "loose matching".
  
- Second, if the routes loose match, then compare the latitude and longitude data more closely using a [dynamic time
  warping](https://en.wikipedia.org/wiki/Dynamic_time_warping) algorithm. We call this "tight matching".
  
Because it can take a while (usually a few seconds) to compare two given activities, we don't compare every new activity
against every existing activity. Instead, we maintain a list of "prototype" activities against which we compare new
activities. If a new activity tight matches a prototype activity, it is considered to match that prototype and every
other activity that matches the same prototype. If a new activity does not match any existing prototype, it becomes a
prototype itself.