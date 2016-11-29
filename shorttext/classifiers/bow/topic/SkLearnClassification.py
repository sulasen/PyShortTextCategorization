from collections import defaultdict

from sklearn.externals import joblib

from utils import textpreprocessing as textpreprocess
from classifiers.bow.topic.LatentTopicModeling import LatentTopicModeler
import utils.classification_exceptions as e

class TopicVectorSkLearnClassifier:
    """
    This is a classifier that wraps any supervised learning algorithm in `scikit-learn`,
    and use the topic vectors output by the topic modeler :class:`LatentTopicModeler` that
    wraps the topic models in `gensim`.
    """
    def __init__(self, topicmodeler, sklearn_classifier):
        """ Initialize the classifier.

        :param topicmodeler: a topic modeler
        :param sklearn_classifier: a scikit-learn classifier
        :type topicmodeler: LatentTopicModeler
        :type sklearn_classifier: sklearn.base.BaseEstimator
        """
        self.topicmodeler = topicmodeler
        self.classifier = sklearn_classifier
        self.trained = False

    def train(self, classdict, *args, **kwargs):
        """ Train the classifier.

        If the topic modeler does not have a trained model, it will raise `ModelNotTrainedException`.

        :param classdict: training data
        :param args: arguments to be passed to the `fit` method of the scikit-learn classifier
        :param kwargs: arguments to be passed to the `fit` method of the scikit-learn classifier
        :return: None
        :raise: ModelNotTrainedException
        :type classdict: dict
        """
        X = []
        y = []
        self.classlabels = classdict.keys()
        for classidx, classlabel in zip(range(len(self.classlabels)), self.classlabels):
            topicvecs = map(self.topicmodeler.retrieve_topicvec, classdict[classlabel])
            X += topicvecs
            y += [classidx]*len(topicvecs)
        self.classifier.fit(X, y, *args, **kwargs)
        self.trained = True

    def getvector(self, shorttext):
        """ Retrieve the topic vector representation of the given short text.

        If the topic modeler does not have a trained model, it will raise `ModelNotTrainedException`.

        :param shorttext: short text
        :return: topic vector representation
        :raise: ModelNotTrainedException
        :type shorttext: str
        :rtype: numpy.ndarray
        """
        if not self.trained:
            raise e.ModelNotTrainedException()
        return self.topicmodeler.retrieve_topicvec(shorttext)

    def classify(self, shorttext):
        """ Give the highest-scoring class of the given short text according to the classifier.

        If neither :func:`~train` nor :func:`~loadmodel` was run, or if the
        topic model was not trained, it will raise `ModelNotTrainedException`.

        :param shorttext: short text
        :return: class label of the classification result of the given short text
        :raise: ModelNotTrainedException
        :type shorttext: str
        :rtype: str
        """
        if not self.trained:
            raise e.ModelNotTrainedException()
        topicvec = self.getvector(shorttext)
        return self.classlabels[self.classifier.predict([topicvec])[0]]

    def score(self, shorttext, default_score=0.0):
        """ Calculate the score, which is the cosine similarity with the topic vector of the model,
        of the short text against each class labels.

        If neither :func:`~train` nor :func:`~loadmodel` was run, or if the
        topic model was not trained, it will raise `ModelNotTrainedException`.

        :param shorttext: short text
        :param default_score: default score if no score is assigned (Default: 0.0)
        :return: dictionary of scores of the text to all classes
        :raise: ModelNotTrainedException
        :type shorttext: str
        :type default_score: float
        :rtype: dict
        """
        if not self.trained:
            raise e.ModelNotTrainedException()
        scoredict = defaultdict(lambda : default_score)
        topicvec = self.getvector(shorttext)
        for classidx, classlabel in zip(range(len(self.classlabels)), self.classlabels):
            scoredict[classlabel] = self.classifier.score([topicvec], [classidx])
        return dict(scoredict)

    def savemodel(self, nameprefix):
        """ Save the model.

        Save the topic model and the trained scikit-learn classification model. The scikit-learn
        model will have the name `nameprefix` followed by the extension `.pkl`. The
        topic model is the same as the one in `LatentTopicModeler`.

        If neither :func:`~train` nor :func:`~loadmodel` was run, or if the
        topic model was not trained, it will raise `ModelNotTrainedException`.

        :param nameprefix: prefix of the paths of the model files
        :return: None
        :raise: ModelNotTrainedException
        :type nameprefix: str
        """
        if not self.trained:
            raise e.ModelNotTrainedException()
        self.topicmodeler.savemodel(nameprefix)
        joblib.dump(self.classifier, nameprefix+'.pkl')

    def loadmodel(self, nameprefix):
        """ Load the classification model together with the topic model.

        :param nameprefix: prefix of the paths of the model files
        :return: None
        :type nameprefix: str
        """
        self.topicmodeler.loadmodel(nameprefix)
        self.classifier = joblib.load(nameprefix+'.pkl')

def train_topicvec_sklearnclassifier(classdict,
                                     nb_topics,
                                     sklearn_classifier,
                                     preprocessor=textpreprocess.standard_text_preprocessor_1(),
                                     topicmodel_algorithm='lda',
                                     toweigh=True,
                                     normalize=True,
                                     gensim_paramdict={},
                                     sklearn_paramdict={}):
    """ Train the supervised learning classifier, with features given by topic vectors.

    It trains a topic model, and with its topic vector representation, train a supervised
    learning classifier. The instantiated (not trained) scikit-learn classifier must be
    passed into the argument.

    :param classdict: training data
    :param nb_topics: number of topics in the topic model
    :param sklearn_classifier: instantiated scikit-learn classifier
    :param preprocessor: function that preprocesses the text (Default: `utils.textpreprocess.standard_text_preprocessor_1`)
    :param topicmodel_algorithm: topic model algorithm (Default: 'lda')
    :param toweigh: whether to weigh the words using tf-idf (Default: True)
    :param normalize: whether the retrieved topic vectors are normalized (Default: True)
    :param gensim_paramdict: arguments to be passed on to the `train` method of the `gensim` topic model
    :param sklearn_paramdict: arguments to be passed on to the `fit` method of the `sklearn` classification algorithm
    :return: a trained classifier
    :type classdict: dict
    :type nb_topics: int
    :type sklearn_classifier: sklearn.base.BaseEstimator
    :type preprocessor: function
    :type topicmodel_algorithm: str
    :type toweigh: bool
    :type normalize: bool
    :type gensim_paramdict: dict
    :type sklearn_paramdict: dict
    :rtype: TopicVectorSkLearnClassifier
    """
    # topic model training
    topicmodeler = LatentTopicModeler(preprocessor=preprocessor,
                                      algorithm=topicmodel_algorithm,
                                      toweigh=toweigh,
                                      normalize=normalize)
    topicmodeler.train(classdict, nb_topics, **gensim_paramdict)

    # intermediate classification training
    classifier = TopicVectorSkLearnClassifier(topicmodeler, sklearn_classifier)
    classifier.train(classdict, **sklearn_paramdict)

    return classifier

def load_topicvec_sklearnclassifier(nameprefix,
                                    preprocessor=textpreprocess.standard_text_preprocessor_1(),
                                    normalize=True):
    """ Load the classifier, a wrapper that uses scikit-learn classifier, with
     feature vectors given by a topic model, from files.

    :param nameprefix: prefix of the paths of model files
    :param preprocessor: function that preprocesses the text (Default: `utils.textpreprocess.standard_text_preprocessor_1`)
    :param normalize: whether the retrieved topic vectors are normalized (Default: True)
    :return: a trained classifier
    :type nameprefix: str
    :type preprocessor: function
    :type normalize: bool
    :rtype: TopicVectorSkLearnClassifier
    """
    # loading topic model
    topicmodeler = LatentTopicModeler(preprocessor=preprocessor, normalize=normalize)
    topicmodeler.loadmodel(nameprefix)

    # loading intermediate model
    sklearn_classifier = joblib.load(nameprefix+'.pkl')

    # the wrapped classifier
    classifier = TopicVectorSkLearnClassifier(topicmodeler, sklearn_classifier)
    classifier.trained = True

    return classifier