from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, SelectField, SubmitField
from wtforms.validators import DataRequired

class ConfigForm(FlaskForm):

    data_dir = StringField('Base directory for storing data', [DataRequired()])
    user_name = StringField('Your name', [DataRequired()])
    distance_unit = SelectField('Preferred unit of distance', choices=(('kilometre', 'km'), ('mile', 'mile')))
    match_center_threshold = FloatField('Threshold for centre-matching of routes')
    match_length_threshold = FloatField('Threshold for length-matching of routes')
    tight_match_threshold = FloatField('Threshold for tight-matching of routes')
    default_activity_name_format = StringField('Format for displaying an activity name', [DataRequired()])
    week_start = SelectField('The first day of the week',
                             choices=('Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'))
    submit = SubmitField('Save')
