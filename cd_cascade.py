# Point of this is to copy audiobooks from CDs to mp3s without having to touch the keyboard between discs, just push the tray back in and come back for the next.

import cdio, pycdio
from io import BytesIO
from os import path, getcwd, makedirs
from pydub import AudioSegment
from time import sleep

def exp_as( audio, this_format, this_track_string, output_directory ):
    audio.export( path.join( output_directory, ( this_track_string + "." + this_format ) ), format=this_format ) # Make sure to create the directory first
    print( "Track saved" )

def get_segment( cd, lsn_start, desired_blocks ):
    read_mode = pycdio.READ_MODE_AUDIO
    # Recommended function for audio/CD-DA - cdio_obj.read_sectors() or pycdio's directly: pycdio.read_sectors( cdio_obj.cd, size, lsn, read_mode )
    blocks, data1 = cd.read_sectors( lsn_start, read_mode, desired_blocks )
    if blocks != -1:
        # Pain to figure this part out 
        return AudioSegment.from_raw( BytesIO( bytes( data1.encode( 'utf-8', errors='surrogateescape' ) ) ), sample_width=2, frame_rate=44100, channels=2 ) 
    else:
        print("-bad data-")

def save_sectors_as_track( cd, track_num, output_directory, this_track_string, output_format, last_track=False ):
    this_track = cd.get_track( track_num )
    if this_track.get_format() == 'audio': 
        print( "Ripping track", track_num, "...", "Starting MSF:", this_track.get_msf(), "Seconds in Track:", this_track.get_track_sec_count() )
        
        # Get necessary track information to read
        lsn_start = this_track.get_lsn()
        try:
            lsn_end = this_track.get_last_lsn()
        except:
            if last_track:
                lsn_end = pycdio.get_disc_last_lsn( cd.cd )

        max_blocks = lsn_end - lsn_start + 1
        max_size = pycdio.ISO_BLOCKSIZE * max_blocks
        read_mode = pycdio.READ_MODE_AUDIO
        desired_blocks = 55

        lsn_start += desired_blocks
        total_blocks = desired_blocks

        audio = get_segment( cd, lsn_start, desired_blocks )
        
        while lsn_start < lsn_end :
            if( lsn_start + 55 <= lsn_end):
                desired_blocks = 55                                 
            else:
                desired_blocks = lsn_end - lsn_start
            not_successful = True
            times_attempted = 0
            while not_successful:
                times_attempted += 1
                try:                                                # Disc stability issue after dropping...
                    new_audio = get_segment( cd, lsn_start, desired_blocks )
                    not_successful = False
                except:
                    if times_attempted == 50:
                        print( "Disc issue" )
                        break
                    else:
                        pass
            audio = audio + new_audio
            lsn_start += desired_blocks
            total_blocks += desired_blocks
        exp_as( audio, output_format, this_track_string, output_directory )
        
def set_up():
    global python_path, disc, output_format, author, book, output_directory, starting_track #, cwd swap with python_path if you want files to go where you're 
                                                                                            #   running from, instead of where the file is
    python_path = path.dirname( path.realpath(__file__) )                                   # The idea is for you to put this script in the same 
                                                                                            #   directory that your audiobooks will go in 

    output_format = "mp3"                                                                   # pydub/AudioSegment can handle other formats

    #print( "reading", pycdio.get_device() )                                                # If you want to know how pycdio refers to your drive

    author = input( "Author:" )                                                             # Top folder
    book = input( "Book:" )                                                                 # Folder in that folder, because authors make multiple books... 
    output_directory = "Disc/" + author + "/" + book + "/"
    makedirs(output_directory, exist_ok=True)

    spec = input( "Special Instructions? (y/n): " )                                         # Ask if user wants to specify disc/track to start on 
    if spec == "y" or spec == "Y":  
        #loop this until usable data?: nah
        disc = int(input( "Start at disc:" ) ) - 1
        starting_track = int( input( "Start at track: ").strip() or 0 )                     # Might add stopping disc/track, but that seems against my current goal
    else:
        disc = 0
        starting_track = 1
    
def main():                                                                                 # unnecessary, but this is coming from C/C++
    set_up()
    global python_path, disc, output_format, author, book, output_directory#, cwd           # decisions were made, it works, I'm not getting paid
    
    cd = cdio.Device(driver_id=pycdio.DRIVER_LINUX)                                         # Initialize the CD drive
    
    # Encapsulate in loop until ctrl+c, because that's how I want it.  No extra interaction per disc.
    while True:    
        try:                                                                                # See if there's a readable disc.
            cd.open()
            cd.get_disc_mode()
        except:
            print( "Waiting on Disc.  " )                                                   # Nice, annoying reminder
        else: 
            that_tracks = cd.get_num_tracks()
            print( "*"*48 )
            disc += 1
                        
            track_string = "Disc" + str( disc ).zfill(2) + "-Track"                         # Eventual filename
            print( "Found Disc, sending", that_tracks, "tracks to:" )                       # Tell user where their files are going
            print( python_path + "/" + output_directory + track_string + "XX" + "." + output_format )
            
            for track_num in range( starting_track, that_tracks +1 ):                       # 
                this_track_string = track_string + str( track_num ).zfill(2)                # eventual filename

                print( "Track:", str( track_num ).zfill(2), "/", str( that_tracks ).zfill(2) , "-", this_track_string + "." + output_format )
                
                if track_num == that_tracks:                                                # Sometimes last track has wonky data for ending lsn
                    last_track = True
                else:
                    last_track = False
                
                save_sectors_as_track( cd, track_num, output_directory, this_track_string, output_format, last_track )
                
            cd.eject_media_drive()

        sleep(30)
            
    cd.close()

main()

# Alternately, I could supply a gui, but I'd rather just make a desktop link to this and let it go
