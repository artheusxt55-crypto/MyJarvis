from openjarvis.engine._base import InferenceEngine
print('InferenceEngine.__init__:', InferenceEngine.__init__)
print('MRO:', [c.__name__ for c in InferenceEngine.__mro__])