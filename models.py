from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from app import app
from db import db
from flask_login import LoginManager, UserMixin

login_manager = LoginManager(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    __tablename__ = 'users'

    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True)
    creator_name = db.Column(db.String(255), unique=True)
    band_name = db.Column(db.String(255), unique=False)
    password = db.Column(db.String(255))
    email = db.Column(db.String(255), unique=True)
    is_authenticated = db.Column(db.Boolean, default=False)
    is_blacklisted = db.Column(db.Boolean, default=False)
    is_deleted = db.Column(db.Boolean, default=False)
    is_creator = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)

    # Relationships
    playlists = db.relationship('Playlist', back_populates='user')
    albums = db.relationship('Album', backref='user', lazy=True)
    songs = db.relationship('Song', backref='user', lazy=True)
    
    # New relationship with PlaylistSongs

    def __init__(self, username, email, password):
        self.username = username
        self.email = email
        self.password = password

    def is_active(self):
        return True

    def get_id(self):
        return self.user_id

    def is_authenticated(self):
        return self.authenticated

    def is_anonymous(self):
        return False
    
    def delete_user(self):
        # Delete associated songs and disassociate from playlists
        for song in self.songs:
            # Disassociate ratings
            for rating in song.rating:
                db.session.delete(rating)

            # Disassociate from playlists
            for playlist_song in song.playlist_songs_association:
                db.session.delete(playlist_song)

            # Delete the song
            db.session.delete(song)

        # Delete associated albums and disassociate from songs
        for album in self.albums:
            for song in album.songs:
                # Disassociate ratings
                for rating in song.rating:
                    db.session.delete(rating)

                # Disassociate from playlists
                for playlist_song in song.playlist_songs_association:
                    db.session.delete(playlist_song)

                # Delete the song
                db.session.delete(song)

            # Delete the album
            db.session.delete(album)

        # Disassociate from playlists directly
        # self.playlists.clear()

        # Remove user_id from playlists
        for playlist in self.playlists:
            playlist.user_id = None

        # Delete the user
        db.session.delete(self)
        db.session.commit()



class Album(db.Model):
    __tablename__ = 'albums'
    album_id = db.Column(db.Integer, primary_key=True)
    album_name = db.Column(db.String(255), nullable=False)
    create_date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'))
    songs = db.relationship('Song', backref='album', lazy=True)

    def __init__(self, album_name, user_id):
        self.album_name = album_name
        self.user_id = user_id

    def get_songs(self):
        return Song.query.filter_by(album_id=self.album_id).all()
    
    def delete_album(self):
        # Disassociate songs and their ratings
        for song in self.songs:
            # Disassociate ratings
            for rating in song.rating:
                db.session.delete(rating)

            # Disassociate from playlists
            for playlist_song in song.playlist_songs_association:
                db.session.delete(playlist_song)

            # Delete the song
            db.session.delete(song)

        # Delete the album
        db.session.delete(self)
        db.session.commit()


class Rating(db.Model):
    __tablename__ = 'ratings'
    rating_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id',ondelete='CASCADE'), nullable=False)
    song_id = db.Column(db.Integer, db.ForeignKey('songs.song_id',ondelete='CASCADE'), nullable=False)
    value = db.Column(db.Integer, nullable=False,default=0)
    song = db.relationship('Song', back_populates='rating', lazy=True)

class Song(db.Model):
    __tablename__ = 'songs'
    song_id = db.Column(db.Integer, primary_key=True)
    song_name = db.Column(db.String(255), nullable=False)
    song_filepath = db.Column(db.String(255), nullable=False)
    lyrics = db.Column(db.Text)
    duration = db.Column(db.String(255))
    create_date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'))
    genre = db.Column(db.String(255))
    creator = db.Column(db.String(255))
    
    playlist_songs_association = db.relationship('PlaylistSongs', back_populates='song', lazy=True)
    # Establish a relationship between Song and Rating
    playlists = db.relationship('Playlist', secondary='playlist_songs', back_populates='songs', lazy=True)
    rating = db.relationship('Rating', back_populates='song', lazy=True)
    album_id = db.Column(db.Integer, db.ForeignKey('albums.album_id'))

    def delete_song(self):
        # Disassociate from playlists
        for playlist_song in self.playlist_songs_association:
            db.session.delete(playlist_song)

        # Disassociate ratings
        for rating in self.rating:
            db.session.delete(rating)

        # Delete the song
        db.session.delete(self)
        db.session.commit()

    

    def average_rating(self):
        all_ratings = [rating.value for rating in self.rating]
        return sum(all_ratings) // len(all_ratings) if len(all_ratings) > 0 else 0
    
    def user_rating(self, user_id):
        rating = Rating.query.filter_by(song_id=self.song_id, user_id=user_id).first()
        return rating.value if rating else None

class Playlist(db.Model):
    __tablename__ = 'playlists'

    playlist_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id',ondelete='CASCADE'))
    user = db.relationship('User', backref='user_playlists')
    songs = db.relationship('Song', secondary='playlist_songs', back_populates='playlists')
    playlist_songs = db.relationship('PlaylistSongs', back_populates='playlist',cascade='all, delete-orphan', lazy=True)
    # songs = db.relationship('Song', secondary='playlist_songs', backref='playlists', lazy=True)

# PlaylistSongs Model
class PlaylistSongs(db.Model):
    __tablename__ = 'playlist_songs'
    
    # Composite primary key
    playlist_id = db.Column(db.Integer, db.ForeignKey('playlists.playlist_id',ondelete='CASCADE'), primary_key=True)
    song_id = db.Column(db.Integer, db.ForeignKey('songs.song_id',ondelete='CASCADE'), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id',ondelete='CASCADE'), nullable=False)
    
    # Define the relationships to Song and Playlist
    song = db.relationship('Song', back_populates='playlist_songs_association', lazy=True)
    playlist = db.relationship('Playlist', back_populates='playlist_songs', lazy=True)

