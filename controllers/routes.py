import os
from app import app
from forms import *
from flask import render_template, url_for, flash, redirect, request
from flask_login import login_required, login_user, current_user,logout_user
from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
from models import *
from sqlalchemy import or_
from controllers.utilities import *
from sqlalchemy.orm import backref,joinedload
bcrypt= Bcrypt(app)

@app.route("/")
def index():
    form=CreatorRegistrationForm()
    return render_template("index.html",form=form)

@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()

        if user and check_password_hash(user.password, form.password.data):
            login_user(user)

            if user.is_admin==True:
                return redirect(url_for('admin_dashboard'))

            flash('Login successful!', 'success')
            
            return redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')

    return render_template('login.html', title='Login', form=form)


@app.route("/register", methods=['GET', 'POST'])
def register():
    # if current_user.is_authenticated:
    #     return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data)
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)




@app.route("/home", methods=['GET', 'POST'])
def home():
    form = CreatorRegistrationForm()
    add_to_playlist_form = AddToPlaylistForm()

    all_albums = (
        Album.query
        .join(User, User.user_id == Album.user_id)
        .filter(User.is_blacklisted == False)
        .order_by(Album.create_date.desc())
        .limit(10)
        .all()
    )

    latest_songs = (
        Song.query
        .join(User, User.user_id == Song.user_id)
        .filter(User.is_blacklisted == False)
        .order_by(Song.create_date.desc())
        .limit(10)
        .all()
    )

    # Fetch existing playlists from the database
    playlists = Playlist.query.all()
    
    if add_to_playlist_form.validate_on_submit():
        # Create a new playlist
        new_playlist = Playlist(
            name=add_to_playlist_form.name.data,
            description=add_to_playlist_form.description.data,
            user_id=current_user.user_id
        )

        db.session.add(new_playlist)
        db.session.commit()

        # Create an association between the song and the playlist
        playlist_song = PlaylistSongs(
            playlist_id=new_playlist.playlist_id, 
            song_id=add_to_playlist_form.song_id.data,# Make sure to get the appropriate song_id
            user_id=current_user.user_id
        )

        db.session.add(playlist_song)
        db.session.commit()

        flash('Playlist created, and song added to the playlist successfully!', 'success')
        return render_template('playlist.html', playlist=new_playlist)

    return render_template("home.html", current_user=current_user, latest_songs=latest_songs,
                           playlists=playlists, form=form, add_to_playlist_form=add_to_playlist_form, all_albums=all_albums)


@app.route('/user_album_songs/<int:album_id>')
def user_album_songs(album_id):
    # Retrieve the album and its songs based on the album_id
    album = Album.query.get_or_404(album_id)
    album_songs = album.get_songs()

    # Pass the album and its songs to the template
    return render_template('user_album_songs.html', album=album, album_songs=album_songs)

@app.route("/account")
def account():
    playlists = Playlist.query.filter_by(user_id=current_user.user_id).all()
    return render_template('user_profile.html', current_user=current_user, playlists=playlists)

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("index"))

@app.route('/register_creator', methods=['GET', 'POST'])
@login_required
def register_creator():
    form = CreatorRegistrationForm()

    if form.validate_on_submit():
        creator_name = form.creator_name.data
        band_name = form.band_name.data

        # ... (rest of the code remains unchanged)

        # Set is_creator to True for the current user
        current_user.is_creator = True

        # Set the creator_email attribute directly on the User instance
        current_user.creator_name = creator_name
        current_user.band_name = band_name if band_name else "Individual"
        current_user.email = current_user.email

        # Commit the changes
        db.session.commit()
        flash("Registered as creator successfully ! ","success")
        # Redirect to the home page or wherever you want
        return redirect(url_for('creator_dashboard'))

    return render_template('register_creator.html', form=form)


@app.route('/creator_dashboard', methods=['GET', 'POST'])
@login_required
def creator_dashboard():

    # Retrieve the creator's songs ordered by the upload date (latest to oldest)
    creator_songs = Song.query.filter_by(user_id=current_user.user_id).order_by(Song.create_date.desc()).all()

    # Retrieve the creator's albums
    creator_albums = Album.query.filter_by(user_id=current_user.user_id).all()

    if request.method == 'POST':


        if current_user.is_blacklisted:
            flash('You are blacklisted. Cannot perform this action.', 'danger')
            return redirect(url_for('creator_dashboard'))


        if 'delete_album' in request.form:
            # Handle deleting an album directly
            album_id = request.form.get('delete_album')

            # Get the album name
            album = Album.query.filter_by(album_id=album_id).first()
            album_name = album.album_name

            if album_name.lower() == 'singles':
                # Delete all songs in the "Singles" album
                songs_to_delete = Song.query.filter_by(user_id=current_user.user_id, album_id=album_id).all()
                for song in songs_to_delete:
                    db.session.delete(song)

                # Commit changes to the database
                db.session.commit()

            # Delete the album and commit changes to the database
            Album.query.filter_by(album_id=album_id).delete()
            db.session.commit()

            flash(f'Album "{album_name}" deleted successfully with all songs!', 'success')
            return redirect(url_for('creator_dashboard'))

        elif 'move_songs_to_singles' in request.form:
            # Handle moving songs to "Singles" album
            album_id = request.form.get('move_songs_to_singles')

            # Check if the album being deleted is the "Singles" album
            album = Album.query.filter_by(album_id=album_id).first()
            album_name = album.album_name
            if album_name.lower() != 'singles':
                singles_album = Album.query.filter_by(album_name='Singles', user_id=current_user.user_id).first()
                if not singles_album:
                    singles_album = Album(album_name='Singles', user_id=current_user.user_id)
                    db.session.add(singles_album)
                    db.session.commit()

                songs_to_move = Song.query.filter_by(user_id=current_user.user_id, album_id=album_id).all()
                for song in songs_to_move:
                    song.album_id = singles_album.album_id

                # Delete the album and commit changes to the database
                Album.query.filter_by(album_id=album_id).delete()
                db.session.commit()

                flash('Album deleted, and songs moved to "Singles" album successfully', 'success')
                return redirect(url_for('creator_dashboard'))
            else:
                flash('Cannot move songs from the "Singles" album!', 'danger')
                return redirect(url_for('creator_dashboard'))

        elif 'edit_album' in request.form:
            # Handle editing album name
            album_id = request.form.get('edit_album')
            new_album_name = request.form.get('new_album_name')

            album = Album.query.get_or_404(album_id)
            album.album_name = new_album_name
            db.session.commit()

            flash('Album name updated successfully', 'success')
            return redirect(url_for('creator_dashboard'))

    return render_template('creator_dashboard.html', creator_songs=creator_songs, creator_albums=creator_albums)

@app.route('/upload_song', methods=['GET', 'POST'])
def upload_song():
    form = UploadSongForm()
    
    if form.validate_on_submit():

        if current_user.is_blacklisted:
            flash('You are blacklisted and cannot upload songs.', 'danger')
            return "<h1>Cannot add songs as you are blacklisted by the admin</h1>"
 
        song_file = form.song_file.data
        song_title = save_song_file(song_file)

        # Get the album name from the form, use a default if not provided
        album_name = form.album_name.data or "Singles"

        # Check if the album exists, if not, create it
        album = Album.query.filter_by(album_name=album_name, user_id=current_user.user_id).first()
        if not album:
            album = Album(album_name=album_name, user_id=current_user.user_id)
            db.session.add(album)
            db.session.commit()

        # Calculate the duration of the song
        duration = get_audio_duration(song_file)

        # Create a new Song instance and add it to the database
        song = Song(
            song_name=form.title.data,
            lyrics=form.lyrics.data,
            duration=duration,
            create_date=datetime.utcnow(),
            user_id=current_user.user_id,
            song_filepath=song_title,
            album_id=album.album_id,
            creator=current_user.creator_name,
            genre=form.genre.data # Assign the song to the created or existing album
        )

        db.session.add(song)
        db.session.commit()

        flash('Song uploaded successfully!', 'success')
        return redirect(url_for('creator_dashboard'))

    return render_template('upload_song.html', title='Upload a Song', form=form)

@app.route('/album/<int:album_id>/songs')
@login_required
def album_songs(album_id):
    # Retrieve the songs of the specified album
    album = Album.query.get_or_404(album_id)
    album_songs = album.songs

    return render_template('album_songs.html', album=album, album_songs=album_songs)

@app.route("/rate_song/<int:song_id>", methods=['POST'])
@login_required
def rate_song(song_id):
    song = Song.query.get(song_id)

    if song:
        # Retrieve the rating value from the form
        new_rating_value = int(request.form.get('rating'))

        # Check if the user has already rated this song
        existing_rating = Rating.query.filter_by(user_id=current_user.user_id, song_id=song.song_id).first()

        if existing_rating:
            # Update the existing rating value
            existing_rating.value = new_rating_value
        else:
            # Create a new Rating object for the current user and rating value
            new_rating = Rating(user_id=current_user.user_id, song_id=song.song_id, value=new_rating_value)

            # Add the new rating to the song's ratings
            song.rating.append(new_rating)

        # Commit the changes to the database
        db.session.commit()

        flash('Rating submitted successfully!', 'success')
    else:
        flash('Song not found!', 'danger')

    return redirect(url_for('home'))

    

@app.route('/update_song/<int:song_id>', methods=['GET', 'POST'])
def update_song(song_id):
    song = Song.query.get_or_404(song_id)
    form = UploadSongForm(obj=song)
    form.song_id.data = song_id  # Set the song_id in the form

    if form.validate_on_submit():
        # Remove associated ratings
        Rating.query.filter_by(song_id=song_id).delete()

        # Populate the song instance with form data
        form.populate_obj(song)

        # Handle file upload
        if form.song_file.data:
            # Save the new MP3 file and update the song file path
            song_file_path = save_song_file(form.song_file.data)
            song.song_filepath = song_file_path

        # Get the album name from the form, use a default if not provided
        album_name = form.album_name.data or "Singles"

        # Check if the album exists, if not, create it
        album = Album.query.filter_by(album_name=album_name, user_id=current_user.user_id).first()
        if not album:
            album = Album(album_name=album_name, user_id=current_user.user_id)
            db.session.add(album)
            db.session.commit()

        # Assign the song to the created or existing album
        song.album_id = album.album_id

        song.song_name = form.title.data
        song.genre = form.genre.data
        song.creator = current_user.creator_name
        
        # Calculate the duration of the song
        duration = get_audio_duration(form.song_file.data)
        song.duration = duration

        # Commit changes to the database
        db.session.commit()

        flash('Song updated successfully', 'success')
        return redirect(url_for('creator_dashboard'))

    return render_template('upload_song.html', title='Update Song', form=form)


@app.route('/delete_song/<int:song_id>')
def delete_song(song_id):
    song = Song.query.get_or_404(song_id)

    # Delete associated ratings first to avoid the NOT NULL constraint
    Rating.query.filter_by(song_id=song_id).delete()

    # Delete the song from the database
    db.session.delete(song)
    db.session.commit()

    return redirect(url_for('album_songs', album_id=song.album_id))


@app.route('/search_results')
def search_results():

    rating_form = SongRatingForm()
    add_to_playlist_form = AddToPlaylistForm()
    
    search_name = request.args.get('search_name')
    search_creator = request.args.get('search_creator')
    search_genre = request.args.get('search_genre')

    results = Song.query.join(Album).filter(
        or_(
            Song.song_name.ilike(f"%{search_name}%"),
            Album.album_name.ilike(f"%{search_name}%")
        ) if search_name else True,
        Song.creator.ilike(f"%{search_creator}%") if search_creator else True,
        Song.genre.ilike(f"%{search_genre}%") if search_genre else True
    ).all()

    return render_template('search_results.html', results=results,rating_form=rating_form, add_to_playlist_form=add_to_playlist_form)

@app.route('/admin')
def admin_dashboard():
    # Fetch statistics
    users = User.query.all()
    creators = User.query.filter(User.is_creator == True).all()
    songs = Song.query.all()
    albums = Album.query.all()
    total_users = User.query.count()
    total_creators = User.query.filter(User.is_creator == True).count()
    total_albums = Album.query.count()


    return render_template('admin_dashboard.html',  users=users, creators=creators, songs=songs, albums=albums, total_users=total_users, total_creators=total_creators, total_albums=total_albums)



@app.route('/admin/delete_song/<int:song_id>')
def admin_delete_song(song_id):
    song = Song.query.options(
        joinedload(Song.playlist_songs_association),
        joinedload(Song.rating)
    ).get_or_404(song_id)
    
    # Use the delete_song method to handle deletion
    song.delete_song()

    flash('Song deleted successfully', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/delete_album/<int:album_id>')
def admin_delete_album(album_id):
    album = Album.query.get_or_404(album_id)

    # Use the delete_album method to handle deletion
    album.delete_album()

    flash('Album deleted successfully', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/album/<int:album_id>')
def admin_album(album_id):
    album = Album.query.get_or_404(album_id)
    return render_template('admin_album.html', album=album)

@app.route("/admin/delete_user/<int:user_id>", methods=['GET', 'POST'])
@login_required
def admin_delete_user(user_id):
    if not current_user.is_admin:
        # Redirect to some unauthorized page or display an error message
        return redirect(url_for('home'))

    user = User.query.get_or_404(user_id)
    if user:
        # Use the delete_user method to handle deletion
        user.delete_user()

        flash(f'User {user.username} has been deleted!', 'success')

    else:
        flash('User not found!', 'error')

    return redirect(url_for('admin_dashboard'))
        
@app.route("/admin/blacklist_creator/<int:user_id>", methods=['GET','POST'])
@login_required
def admin_blacklist_creator(user_id):
    if not current_user.is_admin:
        # Redirect to some unauthorized page or display an error message
        return redirect(url_for('home'))

    user = User.query.get(user_id)
    if user and user.is_creator:
        user.is_blacklisted = True
        db.session.commit()
        flash(f'Creator {user.creator_name} has been blacklisted!', 'success')
    else:
        flash('Creator not found or is not a creator!', 'error')

    return redirect(url_for('admin_dashboard'))

# Admin route to whitelist a creator
@app.route("/admin/whitelist_creator/<int:user_id>", methods=['GET','POST'])
@login_required
def admin_whitelist_creator(user_id):
    if not current_user.is_admin:
        # Redirect to some unauthorized page or display an error message
        return redirect(url_for('home'))

    user = User.query.get(user_id)
    if user and user.is_creator:
        user.is_blacklisted = False
        db.session.commit()
        flash(f'Creator {user.creator_name} has been whitelisted!', 'success')
    else:
        flash('Creator not found or is not a creator!', 'error')

    return redirect(url_for('admin_dashboard'))


@app.route('/playlist/<int:playlist_id>')
def playlist(playlist_id):
    playlist = Playlist.query.get(playlist_id)
    
    edit_form = EditPlaylistForm()

    if edit_form.validate_on_submit():
        # Handle form submission
        new_playlist_name = edit_form.name.data
        playlist.name = new_playlist_name
        db.session.commit()
        flash('Playlist name updated successfully!', 'success')
        return redirect(url_for('playlist', playlist_id=playlist_id))
    
    if not playlist:
        # Handle the case where the playlist doesn't exist
        return "No such Playlist"

    # Fetch all songs to set as choices in AddSongToPlaylistForm
    all_songs = Song.query.all()
    
    # Fetch the songs associated with the playlist using direct query
    playlist_songs = Song.query.join(PlaylistSongs).filter_by(playlist_id=playlist_id).all()
    
    # Create the AddSongToPlaylistForm instance and set choices
    form = AddSongToPlaylistForm()
    form.song_ids.choices = [(song.song_id, song.song_name) for song in all_songs]

    return render_template('playlist.html', playlist=playlist, playlist_songs=playlist_songs, form=form, edit_form=edit_form)



@app.route('/add_to_playlist/<int:song_id>', methods=['GET', 'POST'])
def add_to_playlist(song_id):
    song = Song.query.get_or_404(song_id)
    form = AddToPlaylistForm()

    if form.validate_on_submit():
        playlist_name = form.name.data
        playlist_description = form.description.data

        # Create a new playlist if it doesn't exist
        playlist = Playlist.query.filter_by(name=playlist_name).first()
        if not playlist:
            playlist = Playlist(name=playlist_name, description=playlist_description,user_id=current_user.user_id)
            db.session.add(playlist)
            db.session.commit()

        # Add the song to the playlist
        playlist_song = PlaylistSongs(playlist_id=playlist.playlist_id, song_id=song.song_id,user_id=current_user.user_id)
        db.session.add(playlist_song)
        db.session.commit()

        flash('Song added to playlist successfully!', 'success')
        return redirect(url_for('playlist', playlist_id=playlist.playlist_id))

    return render_template('add_to_playlist.html', song=song, form=form)


@app.route('/edit_playlist/<int:playlist_id>', methods=['POST'])
def edit_playlist(playlist_id):
    playlist = Playlist.query.get_or_404(playlist_id)

    # You might want to add additional checks here, such as checking if the current user owns the playlist.

    new_playlist_name = request.form.get('name')

    playlist.name = new_playlist_name
    db.session.commit()

    flash('Playlist name updated successfully!', 'success')
    return redirect(url_for('playlist', playlist_id=playlist_id))



@app.route('/add_songs_to_playlist/<int:playlist_id>', methods=['GET', 'POST'])
def add_songs_to_playlist(playlist_id):
    form = AddSongToPlaylistForm()

    # Fetch all available songs and use them as choices
    all_songs = Song.query.all()
    form.song_ids.choices = [(song.song_id, song.song_name) for song in all_songs]

    if form.validate_on_submit():
        # Get selected song IDs from the form
        song_ids = form.song_ids.data

        # Add selected songs to the playlist
        playlist = Playlist.query.get(playlist_id)
        for song_id in song_ids:
            playlist_song = PlaylistSongs(playlist_id=playlist_id, song_id=song_id, user_id=current_user.user_id)
            db.session.add(playlist_song)

        # Commit the changes to the database
        db.session.commit()

        # Flash a success message
        flash('Songs added to playlist successfully!', 'success')

        # Redirect to the playlist page
        return redirect(url_for('playlist', playlist_id=playlist_id))

    # If the form is not submitted or not valid, render the template
    return render_template('playlist.html', playlist_id=playlist_id, form=form, all_songs=all_songs)


@app.route('/delete_playlist/<int:playlist_id>', methods=['POST'])
def delete_playlist(playlist_id):
    playlist = Playlist.query.get_or_404(playlist_id)

    # Add additional checks here, such as checking if the current user owns the playlist.

    db.session.delete(playlist)
    db.session.commit()

    flash('Playlist deleted successfully!', 'success')
    return redirect(url_for('account'))