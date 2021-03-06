'''
Created on 25 mai 2018

@author: frup82455
'''
import logging
import logging.config

import math
import numpy as np
import matplotlib.pyplot as plt
import random
import sys
import time
import os
import shutil
from collections import OrderedDict

import const.constants as const
import db.db as db

# Abtract classes
import abc

## Logging
logging.config.fileConfig( 'logging.conf' )
# create logger
logger = logging.getLogger( 'mle' )

# Abstract class
class AbstractMachine():
    # Abstract class
    __metaclass__ = abc.ABCMeta

    APP_KEY     = const.APP_KEY
    APP_KEY_RUN = const.APP_RUN_KEY

    '''
    Abstract Machine Learning class
    '''

    def __init__( self, params = None ):
        '''
        Constructor
        '''

    @abc.abstractmethod
    def modelInit( self, strStructure, X_shape, X_type, Y_type, Y_shape, training ):
        "Initializse the model"

    @abc.abstractmethod
    def getSession( self ):
        "Get a new calculation session"

    @abc.abstractmethod
    def initSessionVariables( self, sess ):
        "Initialize session variables"

    @abc.abstractmethod
    def modelOptimizeEnd( self, session ):
        "End of model optimization"

    @abc.abstractmethod
    def persistModel( self, sess, idRun ):
        "Persist model"

    @abc.abstractmethod
    def restoreModel( self, idRun ):
        "Restore model"

    @abc.abstractmethod
    def accuracyEval( self, XY, what ):
        "Evaluate accurary"

    @abc.abstractmethod
    def correctPredictionEval( self, XY ):
        "Return a 0/1 vector containing correct predictions"

    def addSystemInfo( self, systemInfo ):
        "Add system information"

    def addPerfInfo( self, systemInfo ):
        "Add perf information - nothing done in this class"
        pass

    def setInfos( self, systemInfo, dataInfo ):
        self.systemInfo = systemInfo
        self.dataInfo = dataInfo

    def setData(self, idDataset, datasetTrn, datasetDev ):
        self.idDataset = idDataset
        self.datasetTrn  = datasetTrn
        self.datasetDev  = datasetDev

    def setRunParams( self, runParams ):
        # Nothing to do
        pass

    def train( self,  conn, dataset, config, comment, isUseBestEpoch=True, tune = False, nbTuning = 20, showPlots = True ):
        "Train the model"

        # hyper parameters
        confHyperParams = config.getHyperParams( conn, dataset )

        runHyperParams = {}
        runHyperParams.update( confHyperParams[ "hyperParameters" ] )

        maxBestNbEpoch, maxBestAccuracyDevEpoch = -1, -1
        initialNbEpoch   = runHyperParams[ const.KEY_NUM_EPOCHS ]
        maxBestBeta      = runHyperParams[ const.KEY_BETA ]
        maxBestKeep_prob = runHyperParams[ const.KEY_KEEP_PROB ]
        
        ## Prepare hyper params
        if tune :
            # Tune params
            beta_min = 0.000000000000001
            beta_max = 0.5

            keep_prob_min = 0.5
            keep_prob_max = 1

            tuning= {}

            maxAccuracyDev = -9999999999999
            maxIdRun = -1
        else :
            nbTuning = 1

        # Display hyper parameters info
        logger.info( "Start Learning rate : " + str( runHyperParams[ const.KEY_START_LEARNING_RATE ] ) )
        logger.info( "Num epoch           : " + str( runHyperParams[ const.KEY_NUM_EPOCHS ] ) )
        logger.info( "Minibatch size      : " + str( runHyperParams[ const.KEY_MINIBATCH_SIZE ] ) )
        logger.info( "Beta                : " + str( runHyperParams[ const.KEY_BETA ] ) )
        logger.info( "keep_prob           : " + str( runHyperParams[ const.KEY_KEEP_PROB ] ) )
        logger.info( "isLoadWeights       : " + str( runHyperParams[ const.KEY_USE_WEIGHTS ] ) )

        # Start time
        tsGlobalStart = time.time()

        if tune:
            # make sure seed is unique
            seed = time.time
            random.seed( seed )

        # Nb of pass to run
        nbPass = nbTuning
        
        # Pass used to recalculate training with best epoch
        bestEpochPass = -1
        if ( isUseBestEpoch ) :
            # Add one for best epoch rerun
            nbPass += 1
            # last pass
            bestEpochPass = nbPass
            
        for j in range( 1, nbPass + 1 ) :

            # best epoch run
            if ( j == bestEpochPass ) :
                
                logger.info( "***************************************************************************" )
                logger.info( "Running interrupted gradient descent, nb epochs={0}".format( maxBestNbEpoch ) )
                logger.info( "***************************************************************************" )

                # select best epoch nb
                runHyperParams[ const.KEY_BETA       ] = maxBestBeta
                runHyperParams[ const.KEY_KEEP_PROB  ] = maxBestKeep_prob
                runHyperParams[ const.KEY_NUM_EPOCHS ] = maxBestNbEpoch
                
            else :
                if tune:
                    logger.info( "*****************************" )
                    logger.info( "Tune round " + str( j ) + "/" + str( nbTuning ) )
                    logger.info( "*****************************" )
    
                    # calculate beta
                    logBeta = random.uniform( math.log10( beta_min ), math.log10( beta_max ) )
                    beta = math.pow( 10, logBeta )
                    logger.info( "Beta = " + str( beta ))
    
                    # calculate keep_prob
                    logKeep_prob = random.uniform( math.log10( keep_prob_min ), math.log10( keep_prob_max ) )
                    keep_prob = math.pow( 10, logKeep_prob )
                    logger.info( "keep_prob = " + str( keep_prob ))
    
                    # update hyper params
                    runHyperParams[ const.KEY_BETA         ] = beta
                    runHyperParams[ const.KEY_KEEP_PROB    ] = keep_prob

                
            # Create run

            self.idRun = db.createRun( conn, self.idDataset, config[ "id" ],  runHyperParams )

            # Update run before calling model
            db.updateRunBefore(
                conn, self.idRun,
                comment=comment,
                system_info=self.systemInfo, data_info=self.dataInfo
            )

            # Run model and update DB run with extra info
            accuracyDev, accuracyTrain, bestNbEpoch, bestAccuracyDevEpoch = self.optimizeModel(
                conn, self.idRun,
                config[ "structure" ],
                runHyperParams,
                isCalculateBestEpoch = isUseBestEpoch and ( j != bestEpochPass ),
                show_plot = showPlots and not tune, extractImageErrors = not tune
            )

            # Print run
            run = db.getRun( conn, self.idRun )
            logger.info( "Run stored in DB: " + str( run ) )

            # Update selected run
            db.updateHpRunSelectorForRun( conn, dataset[ "id" ], config[ "id" ], run[ "id" ] )
            conn.commit()

            # Manage best epoch params
            if ( 
                # Using best epoch mode and not in best epoch finalization pass
                isUseBestEpoch and ( j != bestEpochPass ) and
                #  mex of best epoch dev accuracy
                ( bestAccuracyDevEpoch > maxBestAccuracyDevEpoch ) 
            ) :
                # Store it
                maxBestAccuracyDevEpoch = bestAccuracyDevEpoch
                maxBestNbEpoch   = bestNbEpoch
                maxBestBeta      = runHyperParams[ const.KEY_BETA ]
                maxBestKeep_prob = runHyperParams[ const.KEY_KEEP_PROB ]

            if tune :
                # Store results
                tuning[ j ] = {
                    "beta": beta, "keep_prob": keep_prob,
                    "accuracyDev": accuracyDev, "accuracyTrain": accuracyTrain
                }

                # Max
                if ( accuracyDev > maxAccuracyDev ) :
                    maxAccuracyDev = accuracyDev
                    maxHyperParams = tuning[ j ]
                    maxIdRun = self.idRun

                    # get or create hyperparams
                    idMaxHp = db.getOrCreateHyperParams( conn, runHyperParams )
                    # Update config
                    config[ "idHyperParams" ] = idMaxHp
                    # save config
                    db.updateConfig( conn, config )
                    # Update selected run
                    db.updateHpRunSelectorForHp( conn, dataset[ "id" ], config[ "id" ], idMaxHp )

                    # Commit result
                    conn.commit()

                # print max
                logger.info( "Max DEV accuracy: " + str( maxAccuracyDev ) )
                logger.info( "Max hyper params:" )
                logger.info( maxHyperParams )
                logger.info( "Max Best epoch DEV accuracy : " + str( maxBestAccuracyDevEpoch ) )
                logger.info( "Max Best epoch nb           : " + str( maxBestNbEpoch ) )
                
            else :
                # Not in tuning mode
                # if maxBestNbEpoch = nominal nbEpochs, stop last loop
                if ( maxBestNbEpoch == initialNbEpoch ) :
                    # Stop loop
                    break


        # End of loops
        if tune :
            # Print tuning
            logger.info( "Tuning:" , tuning )
            logger.info( "" )
            logger.info( "Max DEV accuracy            : " + str( maxAccuracyDev ) )
            logger.info( "Max Best epoch DEV accuracy : " + str( maxBestAccuracyDevEpoch ) )
            logger.info( "Max Best epoch nb           : " + str( maxBestNbEpoch ) )
            logger.info( "Max hyper params idRun: " + str( maxIdRun ) )

            # Change selected hyper-parameters

            # Get max dev accuracy from all runs
            ( _, absoluteMaxAccuracyDev, _ ) = db.getBestHyperParams( conn, dataset[ "id" ], config[ "id" ] )
            # If our max dev accuracy is better, change current select hps
            if ( absoluteMaxAccuracyDev <= maxAccuracyDev ) :
                db.updateHpRunSelectorForHp( conn, dataset[ "id" ], config[ "id" ], idMaxHp )

        # Commit result
        conn.commit()
        
        # Start time
        tsGlobalEnd = time.time()
        globalElapsedSeconds = int( round( tsGlobalEnd - tsGlobalStart ) )

        logger.info( "Finished in " + str( globalElapsedSeconds ) + " seconds" )

    def predict( self, conn, dataset, config, idRun, imagePathes ):
        "Predict accuracy from trained model"

        # hyper parameters
        confHyperParams = config.getHyperParams( conn, dataset )

        runHyperParams = {}
        runHyperParams.update( confHyperParams[ "hyperParameters" ] )

        logger.info( "Hyper params from run ID:", idRun )
        logger.info( "Hyper params:", runHyperParams )

        # Start time
        tsGlobalStart = time.time()

        # Predict from saved model
        self.predictFromSavedModel( conn, config, idRun, imagePathes )

        # Start time
        tsGlobalEnd = time.time()
        globalElapsedSeconds = int( round( tsGlobalEnd - tsGlobalStart ) )

        logger.info( "Finished in " + globalElapsedSeconds + "seconds" )

    # Stuff to catch Ctrl-C
    def signal_handler( self, signal, frame ):
        logger.info( "Please, wait an epoch before training stops" )
        self.interrupted = True

    def initializeDataset( self, session, dataset ):
        pass

    def optimizeModel(
        self, conn, idRun,
        structure,
        hyperParams,
        print_cost = True, show_plot = True, extractImageErrors = True
    ):

        costs = []                                     # To keep track of the cost
        DEV_accuracies = []                            # for DEV accuracy graph

        # Get hyper parameters from dico
        self.beta           = hyperParams[ const.KEY_BETA ]
        self.keep_prob      = hyperParams[ const.KEY_KEEP_PROB ]
        self.num_epochs     = hyperParams[ const.KEY_NUM_EPOCHS ]
        self.minibatch_size = hyperParams[ const.KEY_MINIBATCH_SIZE ]

        self.start_learning_rate         = hyperParams[ const.KEY_START_LEARNING_RATE ]
        self.learning_rate_decay_nb      = hyperParams[ const.KEY_LEARNING_RATE_DECAY_NB_EPOCH ]
        self.learning_rate_decay_percent = hyperParams[ const.KEY_LEARNING_RATE_DECAY_PERCENT ]

        self.useBatchNormalization = hyperParams[ const.KEY_USE_BATCH_NORMALIZATION ]

        # Convert ( nbLines, dims... ) to ( None, dims... )
        X_shape = [ None ]
        X_shape.extend( self.dataInfo[ const.KEY_TRN_X_SHAPE ][ 1: ] )
        X_type = self.datasetTrn.X.dtype

        Y_shape = [ None ]
        Y_shape.extend( self.dataInfo[ const.KEY_TRN_Y_SHAPE ][ 1: ] )
        Y_type = self.datasetTrn.Y.dtype

        self.modelInit( structure, X_shape, X_type, Y_shape, Y_type, training=True )

        seed = 3 # to keep consistent results

        # Start the session to compute the tensorflow graph

        with self.getSession() as sess:

            # initialize session variables
            self.initSessionVariables( sess )

            # current iteration
            iteration = -1

            ## optimisation may overshoot locally
            ## To avoid returning an overshoot, we detect it and run extra epochs if needed
            finalizationMode = False
            current_num_epochs = hyperParams[ const.KEY_NUM_EPOCHS ]
            iEpoch = 0
            minCost = 99999999999999
            minCostFinalization = 99999999999999
            finished = False

            # When to we display epochs stats
            nbStatusEpoch = math.ceil( current_num_epochs / 20 )

            # intercept Ctrl-C
            self.interrupted = False
            import signal
            # signal.signal( signal.SIGINT, self.signal_handler )

            self.initializeDataset( sess, self.datasetTrn )

            # Start time
            tsStart = time.time()

            # time to make sure we trace something each N minuts
            tsTraceStart = tsStart

            # Do the training loop
            while ( not self.interrupted and not finished and ( iEpoch <= current_num_epochs ) ) :

                epoch_cost = 0.                       # Defines a cost related to an epoch

                if ( self.minibatch_size < 0 ) :

                    # No mini-batch : do a gradient descent for whole data

                    iteration += 1

                    epoch_cost = self.runIteration(
                        iEpoch, 1, sess,
                        self.datasetTrn.X, self.datasetTrn.Y, self.keep_prob,
                    )

                else:

                    # Minibatch mode, non handled by data source
                    m = self.dataInfo[ const.KEY_TRN_X_SIZE ]               # m : number of examples in the train set)
                    num_minibatches =  math.ceil( m / self.minibatch_size ) # number of minibatches of size minibatch_size in the train set
                    seed = seed + 1

                    minibatches = self.random_mini_batches( self.datasetTrn.X, self.datasetTrn.Y, self.minibatch_size, seed )

                    iterationMinibatch = 0

                    for minibatch in minibatches:

                        iteration += 1
                        iterationMinibatch += 1

                        # Select a minibatch
                        (minibatch_X, minibatch_Y) = minibatch

                        minibatch_cost = self.runIteration(
                            sess, ( minibatch_X, minibatch_Y ),
                            iteration, num_minibatches,
                            self.keep_prob
                        )

                        epoch_cost += minibatch_cost / num_minibatches

                        if ( print_cost and iteration == 0 ) :
                            # Display iteration 0 to allow verify cost calculation accross machines
                            logger.info( "Current cost epoch %i; iteration %i; %f" % ( iEpoch, iteration, epoch_cost ) )

                        # time to trace?
                        tsTraceNow = time.time()
                        tsTraceElapsed = tsTraceNow - tsTraceStart

                        # Each 60 seconds
                        if ( tsTraceElapsed >= 60 ) :

                            # Display iteration 0 to allow verify cost calculation accross machines
                            logger.info( "Current cost epoch %i; iteration %i; %f" % ( iEpoch, iteration, epoch_cost ) )
                            # reset trace start
                            tsTraceStart = tsTraceNow

                if print_cost and iEpoch % nbStatusEpoch == 0:
                    logger.info( "Cost after epoch %i; iteration %i; %f" % ( iEpoch, iteration, epoch_cost ) )
                    if ( iEpoch != 0 ) :

                        # Performance counters
                        curElapsedSeconds, curPerfIndex = self.getPerfCounters( tsStart, iEpoch, self.datasetTrn.X.shape )
                        logger.info( "  current: elapsedTime:", curElapsedSeconds, "perfIndex:", curPerfIndex )

                        #  calculate DEV accuracy
                        DEV_accuracy = self.accuracyEval( ( self.datasetDev.X, self.datasetDev.Y ), "dev" )
                        logger.info( "  current: DEV accuracy: %f" % ( DEV_accuracy ) )
                        DEV_accuracies.append( DEV_accuracy )

                if print_cost == True and iEpoch % 5 == 0:
                    costs.append( epoch_cost )

                # Record min cost
                minCost = min( minCost, epoch_cost )

                # Next epoch
                iEpoch += 1
                self.var_numEpoch.load( iEpoch )

                # Close to finish?
                if ( not finalizationMode and ( iEpoch > current_num_epochs ) ) :
                    # Activate finalization mode
                    finalizationMode = True
                    # local overshoot?
                    if ( epoch_cost > minCost ) :
                        # Yes, run some extra epochs
                        logger.warn( "Local cost overshoot detected, adding maximum 100 epochs to leave local cost overshoot" )
                        current_num_epochs += 100
                        minCostFinalization = minCost

                if ( finalizationMode ) :
                    # Check overshoot is finished
                    if ( epoch_cost <= minCostFinalization ) :
                        # finished
                        finished = True

            self.modelOptimizeEnd( sess )

            if ( self.interrupted ) :
                logger.info( "Training has been interrupted by Ctrl-C" )
                logger.info( "Store current epoch number '" + str( iEpoch ) + "' in run hyper parameters" )
                # Get runs and hps
                run = db.getRun( conn, self.idRun )
                idRunHps = run[ "idHyperParams" ]
                runHps = db.getHyperParams( conn, idRunHps )[ "hyperParameters" ]
                # Modify num epochs
                runHps[ const.KEY_NUM_EPOCHS ] = iEpoch
                # update run
                db.updateRun( conn, self.idRun, runHps )

            # Final cost
            print ("Parameters have been trained!")
            logger.info( "Final cost:", epoch_cost )

            ## Elapsed (seconds)
            elapsedSeconds, perfIndex = self.getPerfCounters( tsStart, iEpoch, self.datasetTrn.X.shape )
            perfInfo = {}

            logger.info( "Elapsed (s):", elapsedSeconds )
            logger.info( "Perf index :", perfIndex )

            self.persistModel( sess, idRun )

            accuracyTrain = self.accuracyEval( ( self.datasetTrn.X, self.datasetTrn.Y ), "trn" )
            print ( "Train Accuracy:", accuracyTrain )

            accuracyDev = self.accuracyEval( ( self.datasetDev.X, self.datasetDev.Y ), "dev" )
            print ( "Dev Accuracy:", accuracyDev )

            if ( show_plot ) :
                # plot the cost
                plt.plot(np.squeeze(costs))
                plt.ylabel('cost')
                plt.xlabel('iterations (per tens)')
                plt.title("Start learning rate =" + str( self.start_learning_rate ) )
                plt.show()

                # plot the accuracies
                plt.plot( np.squeeze( DEV_accuracies ) )
                plt.ylabel('DEV accuracy')
                plt.xlabel('iterations (100)')
                plt.title("Start learning rate =" + str( self.start_learning_rate ) )
                plt.show()

            ## Errors
            resultInfo = {}

            if ( extractImageErrors ) :

                # Lists of OK for training
                oks_train  = self.correctPredictionEval( ( self.datasetTrn.X, self.datasetTrn.Y ) )
                map1, map2 = self.statsExtractErrors( "train", dataset = self.datasetTrn, oks = oks_train, show_plot=show_plot )
                # Errors nb by data tag
                resultInfo[ const.KEY_TRN_NB_ERROR_BY_TAG ] = map1
                resultInfo[ const.KEY_TRN_PC_ERROR_BY_TAG ] = map2

                oks_dev   = self.correctPredictionEval( ( self.datasetDev.X, self.datasetDev.Y ) )
                map1, map2 = self.statsExtractErrors( "dev", dataset = self.datasetDev, oks = oks_dev, show_plot=show_plot )
                # Errors nb by data tag
                resultInfo[ const.KEY_DEV_NB_ERROR_BY_TAG ] = map1
                resultInfo[ const.KEY_DEV_PC_ERROR_BY_TAG ] = map2

            # Update DB run after execution, add extra info
            db.updateRunAfter(
                conn, idRun,
                perf_info = perfInfo, result_info=resultInfo,
                perf_index=perfIndex,
                elapsed_second = elapsedSeconds,
                train_accuracy=accuracyTrain.astype( float ),
                dev_accuracy=accuracyDev.astype( float )
            )

            return accuracyDev, accuracyTrain

    def runIteration(
        self,
        iteration, num_minibatches, sess,
        XY, keep_prob
    ):
        # Abstract methode
        raise ValueError( "Abstract method" )

    def random_mini_batches( self, X, Y, mini_batch_size = 64, seed = 0):
        """
        Creates a list of random minibatches from (X, Y)

        Arguments:
        X -- input data, of shape (input size, number of examples)
        Y -- true "label" vector (containing 0 if cat, 1 if non-cat), of shape (1, number of examples)
        mini_batch_size - size of the mini-batches, integer
        seed -- this is only for the purpose of grading, so that you're "random minibatches are the same as ours.

        Returns:
        mini_batches -- list of synchronous (mini_batch_X, mini_batch_Y)
        """

        m = X.shape[0]                  # number of training examples
        mini_batches = []
        np.random.seed( seed )

        # Step 1: Shuffle (X, Y)
        permutation = list( np.random.permutation( m ) )
        shuffled_X = X[ permutation, : ]
        shuffled_Y = Y[ permutation, : ].reshape( ( m, Y.shape[1] ) )

        # Step 2: Partition (shuffled_X, shuffled_Y). Minus the end case.
        num_complete_minibatches = math.floor( m / mini_batch_size) # number of mini batches of size mini_batch_size in your partitioning

        for k in range( 0, num_complete_minibatches ):
            mini_batch_X = shuffled_X[ k * mini_batch_size : k * mini_batch_size + mini_batch_size, : ]
            mini_batch_Y = shuffled_Y[ k * mini_batch_size : k * mini_batch_size + mini_batch_size, : ]

            # Some check: verify maini_batch shapes are OK
            assert ( mini_batch_X.shape[ 1 ] == X.shape[ 1 ] ) # cols nb is OK
            assert ( mini_batch_Y.shape[ 1 ] == Y.shape[ 1 ] ) # cols nb is OK

            mini_batch = (mini_batch_X, mini_batch_Y)
            mini_batches.append( mini_batch )

        # Handling the end case (last mini-batch < mini_batch_size)
        if ( m % mini_batch_size != 0 ) :
            mini_batch_X = shuffled_X[ num_complete_minibatches * mini_batch_size : m, : ]
            mini_batch_Y = shuffled_Y[ num_complete_minibatches * mini_batch_size : m, : ]
            mini_batch = (mini_batch_X, mini_batch_Y)
            mini_batches.append( mini_batch )

        return mini_batches

    def getPerfCounters( self, tsStart, iEpoch, X_real_shape, nbSamples ):

        tsNow = time.time()

        ## Elapsed (seconds)
        elapsedSeconds = int( round( tsNow - tsStart ) )

        # caculate volume : mutiply dimensions
        import operator
        import functools
        volume = functools.reduce( operator.mul, X_real_shape, 1 ) * nbSamples

        # performance index : per iEpoth - per samples
        if ( elapsedSeconds == 0 ) :
            #not available
            perfIndex = float('nan')
        else :
            perfIndex = 1 / ( elapsedSeconds / iEpoch / volume ) * 1e-8

        return elapsedSeconds, perfIndex

    def dumpBadImages( self, correct, dataHome, imgDir, PATH, TAG, errorsDir ):

        nbBadImages = 0

        # Delete files in error dir
        for the_file in os.listdir( errorsDir ):
            file_path = os.path.join( errorsDir, the_file )
            try:
                if os.path.isfile(file_path):
                    os.unlink( file_path )
            except Exception as e:
                logger.error( e )

        # check deleted
        if ( len( os.listdir( errorsDir ) ) != 0 ) :
            logger.info( "Dir", errorsDir, "not empty." )
            sys.exit( 1 )

        # Dico of errors by label
        mapErrorNbByTag = {}

        imgBase = dataHome.replace( "\\", "/" )

        # Extract errors
        for i in range( 0, correct.shape[ 0 ] ):

            # Is an error?
            if ( not( correct[ i ] ) ) :

                nbBadImages += 1

                # finished?
                if ( nbBadImages > 100 ) :
                    break;

                # Add nb
                numpy_label = TAG[ i, 0 ]
                label = numpy_label.decode( 'utf-8' )
                try:
                    nb = mapErrorNbByTag[ label ]
                except KeyError as e:
                    ## Init nb
                    nb = 0

                nb += 1
                mapErrorNbByTag[ label ] = nb

                # extract 64x64x3 image
                #X_errorImg = X_orig[ i ]
                #errorImg = Image.fromarray( X_errorImg, 'RGB' )

                ## dump image
                #errorImg.save( errorsDir + '/error-' + str( i ) + ".png", 'png' )

                # Get original image
                # str: b'truc'
                numpy_imgRelPath = PATH[ i, 0 ]
                # b'truc' -> 'truc'
                imgAbsPath = numpy_imgRelPath.decode( 'utf-8' )

                #imgPath = imgBase + "/" + imgRelPath

                toFile = errorsDir + "/" + label + "-" + str( i ) + "-" + os.path.basename( imgAbsPath )
                shutil.copyfile( imgAbsPath, toFile )

        # return dico
        return mapErrorNbByTag

    def statsExtractErrors( self, key, dataset, oks, show_plot=True ) :

        errorsDir = os.getcwd().replace( "\\", "/" ) + "/errors/" + key

        os.makedirs( errorsDir, exist_ok = True )

        # Delete files in error dir
        for the_file in os.listdir( errorsDir ):

            file_path = os.path.join( errorsDir, the_file )
            try:
                if os.path.isfile(file_path):
                    os.unlink( file_path )
            except Exception as e:
                logger.error( e )

        # check deleted
        if ( len( os.listdir( errorsDir ) ) != 0 ) :
            logger.info( "Dir " + errorsDir + " not empty." )
            sys.exit( 1 )

        # Dump bad images
        mapErrorNbByTag = self.dumpBadImages( oks, dataset.dataHome, dataset.imgDir, dataset.imgPathes, dataset.tags, errorsDir )

        # Sort by value
        mapErrorNbByTagSorted = \
            OrderedDict(
                sorted( mapErrorNbByTag.items(), key=lambda t: t[1], reverse=True )
        )

        ## Error repartition by label
        logger.info( "Nb errors by tag for " + key + ": " + str( mapErrorNbByTagSorted ) )

        # Build %age map
        nbSamples = oks.shape[ 0 ]

        mapErrorPercentNbByTag = {}

        for labelError in mapErrorNbByTagSorted.items() :
            label = labelError[ 0 ]
            percentage = labelError[ 1 ] / nbSamples
            mapErrorPercentNbByTag[ label ] = "{0:.0f}%".format( percentage * 100 )

        # Sort by value
        mapErrorNbPercentByTagSorted = \
            OrderedDict(
                sorted( mapErrorPercentNbByTag.items(), key=lambda t: t[1], reverse=True )
        )

        ## Error repartition by label
        logger.info( "% errors by tag for " + key + ": " + str( mapErrorPercentNbByTag ) )

        ## Graph
        if ( show_plot ) :
            x = np.arange( len( mapErrorNbByTagSorted ) )
            plt.bar( x, mapErrorNbByTagSorted.values() )
            plt.xticks( x, mapErrorNbByTagSorted.keys( ) )
            plt.title( "Error repartition for " + key )
            plt.show()

        return mapErrorNbByTagSorted, mapErrorPercentNbByTag

