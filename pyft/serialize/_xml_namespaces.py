# XML namespace definitions used in parsing / creating GPX and TCX files.

TCX_NAMESPACES = {
    None: 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2',
    'user_profile': 'http://www.garmin.com/xmlschemas/UserProfile/v2',
    'activity_extension': 'http://www.garmin.com/xmlschemas/ActivityExtension/v2',
    'profile_extension': 'http://www.garmin.com/xmlschemas/ProfileExtension/v1',
    'activity_goals': 'http://www.garmin.com/xmlschemas/ActivityGoals/v1',
    'xsi': 'http://www.w3.org/2001/XMLSchema-instance'
}

TCX_SCHEMALOCATION = 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2 '\
                     'http://www.garmin.com/xmlschemas/TrainingCenterDatabasev2.xsd'

# Namespaces are mostly dealt with by the gpxpy library, so these are only the ones we need to use separately.
GPX_NAMESPACES = {
    'garmin_tpe': 'http://www.garmin.com/xmlschemas/TrackPointExtension/v1'
}