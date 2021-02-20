from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import SubmitField


class UploadForm(FlaskForm):

    upload_file = FileField(validators=[
        FileRequired(),
        FileAllowed(['gpx', 'tcx', 'fit'], message='File must be a GPX, TCX or FIT file.')
    ])
    submit = SubmitField('Upload')
