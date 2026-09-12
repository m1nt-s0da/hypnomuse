from transformers import ClapModel, ClapFeatureExtractor, ClapProcessor

__all__ = ["get_feature_extractor", "get_model"]

model_id = "laion/clap-htsat-unfused"

_feature_extractor: ClapFeatureExtractor | None = None
_model: ClapModel | None = None
_processor: ClapProcessor | None = None


def get_feature_extractor():
    global _feature_extractor
    if _feature_extractor is None:
        _feature_extractor = ClapFeatureExtractor.from_pretrained(model_id)

    return _feature_extractor


def get_model(eval=True):
    global _model
    if _model is None:
        _model = ClapModel.from_pretrained(model_id)
        if eval:
            _model.eval()

    return _model


def get_processor():
    global _processor
    if _processor is None:
        _processor = ClapProcessor.from_pretrained(model_id)

    return _processor
