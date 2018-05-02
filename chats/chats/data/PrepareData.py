#!/usr/local/bin/python2.7
# encoding: utf-8
'''
data.PrepareData -- shortdesc

data.PrepareData is a description

It defines classes_and_methods

@author:     user_name

@copyright:  2018 organization_name. All rights reserved.

@license:    license

@contact:    user_email
@deffield    updated: Updated
'''

import sys
import os

import glob
import random
from PIL import Image
import h5py
import numpy as np

import wget
import shutil

from apiclient.discovery import build

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter

__all__ = []
__version__ = 0.1
__date__ = '2018-04-24'
__updated__ = '2018-04-24'

DEBUG = 1
TESTRUN = 0
PROFILE = 0

# Constants
TRAINING_TEST_SET_PC = 0.80

RESIZE_PX = 64

class CLIError(Exception):
    '''Generic exception to raise and log different fatal errors.'''
    def __init__(self, msg):
        super(CLIError).__init__(type(self))
        self.msg = "E: %s" % msg
    def __str__(self):
        return self.msg
    def __unicode__(self):
        return self.msg


def getImage( url, fileName ):
    
    wget.download( url, fileName ) 

def getGoogleImageData():

    # get image
    
    apiKey = "AIzaSyDHVMHUD5776TppEEXTdI8T5kUPFi_HG44"
    
    # Google
    cx = '005180524979857628053:btxxhdgj_ry'
    
    # Google image
    #cx = '005180524979857628053:qtpwfznzde8'
    
    service = build( "customsearch", "v1",
               developerKey=apiKey )

    iCat = 100;
    
    num = 5
    
    for page in range( 200 ):
        
        print( "Page " + str( page ) );
        
        res = service.cse().list(
            q= 'cat',
            cx= cx,
            searchType='image',
            start= page * num + 1,
            num= num,
            imgType='clipart',
            fileType='png',
            safe= 'off'
        ).execute()
    
        if not 'items' in res:
            print( "No result" )
        else:
            for item in res['items']:
                print('{}:\n\t{}'.format(item['title'], item['link']))  
                
                # get image
                url= item['link']
                mime = item[ 'mime' ]
                mime = mime.replace( '/', '.' )
                fileName = "C:/temp/" + "cat-" + str( iCat ) + "-" + mime
                
                try:
                    getImage( url, fileName )
                except:
                    print( "Can't download url '" + url + "'" )
                    
                iCat += 1
            

def transformImages( fromDir, toDir ):
    
    # get files
    files = glob.glob( fromDir + '/cats/**/*.*', recursive=True)
    
    for oriImgFile in files:
        # Copy from image
        toFile = toDir + "/cats/" + os.path.basename( oriImgFile )
        shutil.copyfile( oriImgFile, toFile )
        
        ## Load image 
        img = Image.open( oriImgFile )
        ## Flip verticaly image
        flippedImage = img.transpose( Image.FLIP_LEFT_RIGHT )
        
        ## save it
        toFlippedImage = toDir + "/cats/flipped-" + os.path.basename( oriImgFile ) + ".png"
        flippedImage.save( toFlippedImage, 'png' )
        
    files = glob.glob( fromDir + '/cats/**/*.*', recursive=True)
    
    files = glob.glob( fromDir + '/non-cats/**/*.*', recursive=True)
    for oriImgFile in files:
        # Copy from image
        toFile = toDir + "/non-cats/" + os.path.basename( oriImgFile )
        shutil.copyfile( oriImgFile, toFile )
        
        ## Load image 
        img = Image.open( oriImgFile )
        ## Flip verticaly image
        flippedImage = img.transpose( Image.FLIP_LEFT_RIGHT )
        
        ## save it
        toFlippedImage = toDir + "/non-cats/flipped-" + os.path.basename( oriImgFile ) + ".png"
        flippedImage.save( toFlippedImage, 'png' )

# Create dev and test sets

def buildDataSet( baseDir, files, iStart, iEnd, outFileName ):
    # images list
    imagesList = []
# Y : cat or non-cat
    Y = []
# From first image to dev test set percentage of full list
#for i in range( iEndTestSet ):
    for i in range( iStart, iEnd ):
        
        curImage = files[i]
        # get rid of basedir
        relCurImage = curImage[len(baseDir) + 1:]
        # Cat?
        relCurImage = relCurImage.replace( '\\', '/' )
        isCat = relCurImage.startswith("cats/")
        # load image
        img = Image.open(curImage)
        # Resize image
        resizedImg = img.resize( ( RESIZE_PX, RESIZE_PX ) )
        # populate lists
        pix = np.array(resizedImg)
        # pix.spahe = (64, 64, 3 ) pour éviter les images monochromes
        if (len(pix.shape) < 3):
            print("Skipping image", curImage)
            print("It's not a (NxNx3) image.")
        else:
            imagesList.append( pix )
            Y.append( isCat ) # Image will be saved
    
# Store as binary stuff
    absOutFile = "C:/Users/fran/eclipse-workspace/chats/data/prepared/" + outFileName
    with h5py.File( absOutFile, "w") as dataset:
        dataset["x"] = imagesList
        dataset["y"] = Y

def createTrainAndDevSets():
    
    dataDir = "C:/Users/fran/eclipse-workspace/chats/data"
    # Base dir for cats and not cats images
    baseDir = dataDir + "/images"
    
    transformedDir = dataDir + "/transformed"
    
    ## transform images
    #transformImages( baseDir, transformedDir )
    
    # get files
    files = glob.glob( transformedDir + '/**/*.*', recursive=True)

    # Shuffle files
    random.shuffle( files )
    
    print( "Build TRAINING test set" )
    iEndTrainingSet = int( len( files ) * TRAINING_TEST_SET_PC );
    
    print( "Build TRAINING data set" )
    buildDataSet( transformedDir, files, 0, iEndTrainingSet, "train_signs.h5" )
    
    ## Build DEV data set
    buildDataSet( \
        transformedDir, files, \
        iEndTrainingSet + 1, len( files ) - 1, \
        "dev_signs.h5" \
    )
    
    print( "Finished" );

    
def main(argv=None): # IGNORE:C0111
    '''Command line options.'''

    if argv is None:
        argv = sys.argv
    else:
        sys.argv.extend(argv)

    program_name = os.path.basename(sys.argv[0])
    program_version = "v%s" % __version__
    program_build_date = str(__updated__)
    program_version_message = '%%(prog)s %s (%s)' % (program_version, program_build_date)
    program_shortdesc = __import__('__main__').__doc__.split("\n")[1]
    program_license = '''%s

  Created by user_name on %s.
  Copyright 2018 organization_name. All rights reserved.

  Licensed under the Apache License 2.0
  http://www.apache.org/licenses/LICENSE-2.0

  Distributed on an "AS IS" basis without warranties
  or conditions of any kind, either express or implied.

USAGE
''' % (program_shortdesc, str(__date__))

    try:
        # Setup argument parser
        parser = ArgumentParser(description=program_license, formatter_class=RawDescriptionHelpFormatter)
        parser.add_argument('-V', '--version', action='version', version=program_version_message)

        parser.add_argument( "-command" );
        
        # Process arguments
        args = parser.parse_args()
        
        # check actions
        command = args.command
        if ( "googleImage".equals( command ) ) :
            print( "XXX" )
            # get data
            getGoogleImageData()

            
    except KeyboardInterrupt:
        ### handle keyboard interrupt ###
        return 0
    except Exception as e:
        if DEBUG or TESTRUN:
            raise( e )
        indent = len(program_name) * " "
        sys.stderr.write(program_name + ": " + repr(e) + "\n")
        sys.stderr.write(indent + "  for help use --help")
        return 2

if __name__ == "__main__":
    
    # Make sure random is repeatable
    random.seed( 1 )
    
    #main( sys.argv[ 1: ] )
    
    #getGoogleImageData()
    
    createTrainAndDevSets()
    