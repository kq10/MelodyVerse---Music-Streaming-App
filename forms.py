from flask_wtf import FlaskForm
from wtforms import FileField, HiddenField, SelectField, SelectMultipleField, StringField, PasswordField, SubmitField, BooleanField, TextAreaField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError,NumberRange
from models import *
from flask_wtf.file import FileAllowed, FileRequired
from werkzeug.utils import secure_filename
from wtforms import IntegerField
 




class RegistrationForm(FlaskForm):
    username = StringField('Username',
                           validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password',
                                     validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('That username is taken. Please choose a different one.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('That email is taken. Please choose a different one.')


class LoginForm(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

class CreatorRegistrationForm(FlaskForm):
    creator_name = StringField('Creator Name', validators=[DataRequired()])
    band_name = StringField('Group Name/Band Name (Optional)')
    submit = SubmitField('Register as Creator')

class UploadSongForm(FlaskForm):
    song_id = HiddenField('Song ID')
    title = StringField('Title', validators=[DataRequired()])
    lyrics = StringField('Lyrics', validators=[DataRequired()])
    song_file = FileField('Upload a Song (MP3)', validators=[
        FileRequired(),
        FileAllowed(['mp3'], 'Only MP3 files are allowed!')
    ])
    genre = StringField('Genre', validators=[DataRequired()])
    album_name = StringField('Album Name')  # Add this line for the album name field
    submit = SubmitField('Upload')

class SongRatingForm(FlaskForm):
    rating = IntegerField('Rating', validators=[DataRequired(), NumberRange(min=1, max=5)])

class AddToPlaylistForm(FlaskForm):
    name = StringField('New Playlist')
    description=StringField('description')
    submit = SubmitField('Add to Playlist')

class AddSongToPlaylistForm(FlaskForm):
    # Fetch all available songs and use them as choices
    all_songs = Song.query.all()
    song_ids = SelectMultipleField('Select Songs', validators=[DataRequired()], coerce=int, choices=[(song.song_id, song.song_name) for song in all_songs], render_kw={"class": "form-control"})
    submit = SubmitField('Add to Playlist', render_kw={"class": "btn btn-success"})

class EditPlaylistForm(FlaskForm):
    name = StringField('New Playlist Name', validators=[DataRequired()])
    submit = SubmitField('Save Changes')