"""Plate-text reader: the project's own CRNN (MobileNetV3-Large -> BiLSTM -> CTC).

The network, preprocessing and decoding below mirror train_mobilenet_ocr_kaggle
exactly (CRNN class, prep() and decode()). Imports do not load weights.

  input   : RGB crop, resized to 64 high x 256 wide (INTER_AREA if wider than 256,
            else INTER_LINEAR), /255, ImageNet mean/std, CHW
  output  : CTC over '0-9A-Z' (blank = 0, CHARS[i] -> class i+1)
  decode  : greedy argmax, collapse repeats, drop blanks;
            confidence = mean of the max softmax over the kept characters
"""
ARCH='CRNN mobilenet_v3_large (strides (2,1) at blocks 7,13) + 2x BiLSTM(128) + CTC'
MEAN=(0.485,0.456,0.406)
STD=(0.229,0.224,0.225)

def build_reader(path):
    import torch
    from torch import nn
    from torchvision.models import mobilenet_v3_large
    checkpoint=torch.load(path,map_location='cpu',weights_only=True)
    if checkpoint.get('arch')!=ARCH:
        raise ValueError('Unsupported recognition architecture')
    class CRNN(nn.Module):
        def __init__(self,classes):
            super().__init__()
            feats=mobilenet_v3_large(weights=None).features
            # Same change as training: blocks 7 and 13 downsample height only,
            # so a 64x256 input gives a 2x32 feature map.
            for index in (7,13):
                for module in feats[index].modules():
                    if isinstance(module,nn.Conv2d) and module.stride==(2,2):module.stride=(2,1)
            self.backbone=feats
            self.reduce=nn.Sequential(nn.Conv2d(960,256,1),nn.BatchNorm2d(256),nn.Hardswish())
            self.rnn=nn.LSTM(256,128,num_layers=2,bidirectional=True,batch_first=True,dropout=0.1)
            self.fc=nn.Linear(256,classes)
        def forward(self,x):
            f=self.reduce(self.backbone(x))              # B x 256 x 2 x 32
            f=torch.cat(list(f.unbind(2)),dim=2)         # top row then bottom row -> B x 256 x 64
            out,_=self.rnn(f.permute(0,2,1))
            return self.fc(out)
    chars=checkpoint['chars']
    model=CRNN(len(chars)+1)
    model.load_state_dict(checkpoint['model'],strict=True)
    model.eval()
    return model,chars,(checkpoint['img_w'],checkpoint['img_h'])

def read_crop(reader,image):
    """Read one plate crop (PIL image). Returns (text, confidence)."""
    import cv2, numpy as np, torch
    model,chars,(width,height)=reader
    rgb=np.array(image.convert('RGB'))
    rgb=cv2.resize(rgb,(width,height),interpolation=cv2.INTER_AREA if rgb.shape[1]>width else cv2.INTER_LINEAR)
    x=(rgb.astype(np.float32)/255.-np.array(MEAN,np.float32))/np.array(STD,np.float32)
    x=torch.from_numpy(x.transpose(2,0,1).copy()).unsqueeze(0)
    with torch.inference_mode():
        probabilities=model(x).softmax(-1)[0]
    scores,indices=probabilities.max(-1)
    text=[];confidences=[];previous=0
    for index,score in zip(indices.tolist(),scores.tolist()):
        if index!=0 and index!=previous:
            text.append(chars[index-1]);confidences.append(score)
        previous=index
    return ''.join(text),(sum(confidences)/len(confidences) if confidences else 0.)
