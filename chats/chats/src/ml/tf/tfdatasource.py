'''
Created on 5 juin 2018

@author: LOISON
'''
from ml.cats.cats import CatRawDataSource

import tensorflow as tf
import const

import os
import h5py

class TensorFlowDataSource( CatRawDataSource ):
    '''
    classdocs
    '''

    def __init__( self, params ):
        super().__init__( params )

    def isSupportBatchStreaming( self ) :
        return True

    def getDatasets( self, isLoadWeights, inMemory = False ):

        # Case : images provided, not files
        if ( self.imagePathes != None ) :

            self.getDatasets( isLoadWeights, inMemory=True )

        else :

            # Load from h5py data sets
            if ( self.inMemory ) :
                # tell ancestor
                ( datasetTrn, datasetDev, dataInfo ) = super().getDatasets( isLoadWeights, inMemory=True )
            else :

                # File based

                # Base dir for cats and not cats images
                baseDirTrn  = os.getcwd() + "/" + self.pathTrn
                baseDirDev  = os.getcwd() + "/" + self.pathDev

                with h5py.File( baseDirTrn + "/train_chats-" + str( self.pxWidth ) + "-metadata.h5", "r" ) as dataset_metadata :
                    datasetTrn = self.getDataset( dataset_metadata, None, isLoadWeights, inMemory=False )
                    # Path to TFRecord files
                    datasetTrn.XY = [ baseDirTrn + "/" + dataset_metadata[ "XY_tfrecordPath" ].value.decode( 'utf-8' ) ]
    
                with h5py.File( baseDirDev + "/dev_chats-"   + str( self.pxWidth ) + "-metadata.h5", "r" ) as dataset_metadata :
                    datasetDev = self.getDataset( dataset_metadata, None, isLoadWeights, inMemory=False )
                    # Path to TFRecord files
                    datasetDev.XY = [ baseDirDev + "/" + dataset_metadata[ "XY_tfrecordPath" ].value.decode( 'utf-8' ) ]

                dataInfo = self.getDataInfo( datasetTrn, datasetDev )
        
                dataInfo[ const.constants.KEY_IS_SUPPORT_BATCH_STREAMING ] = True

        # get batch size
        self.batchSize = self.params[ "hyperParameters" ][ const.constants.KEY_MINIBATCH_SIZE ]
        
        return ( datasetTrn, datasetDev, dataInfo )

    read_features = {
        'X': tf.FixedLenFeature( [], dtype=tf.string ),
        'Y': tf.FixedLenFeature( [], dtype=tf.int64 ),
    }

