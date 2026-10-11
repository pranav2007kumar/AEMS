"""Local CRNN reader reconstructed from the supplied checkpoint metadata.

Imports do not load weights. Preprocessing must match the training pipeline;
ANPR_OCR_NORMALIZATION can be unit, half (default) or imagenet.
"""
import os

def build_reader(path):
    import torch
    from torch import nn
    from torchvision.models import mobilenet_v3_large
    checkpoint=torch.load(path,map_location='cpu',weights_only=True)
    if checkpoint.get('arch')!='CRNN mobilenet_v3_large (strides (2,1) at blocks 7,13) + 2x BiLSTM(128) + CTC':
        raise ValueError('Unsupported recognition architecture')
    class CRNN(nn.Module):
        def __init__(self):
            super().__init__()
            self.backbone=mobilenet_v3_large(weights=None).features
            for index in (7,13):self.backbone[index].block[1][0].stride=(2,1)
            self.reduce=nn.Sequential(nn.Conv2d(960,256,1),nn.BatchNorm2d(256),nn.ReLU(inplace=True))
            self.rnn=nn.LSTM(256,128,num_layers=2,bidirectional=True,batch_first=True)
            self.fc=nn.Linear(256,37)
        def forward(self,x):
            x=self.reduce(self.backbone(x)).mean(dim=2).permute(0,2,1)
            x,_=self.rnn(x)
            return self.fc(x)
    model=CRNN()
    model.load_state_dict(checkpoint['model'],strict=True)
    model.eval()
    return model,checkpoint['chars'],(checkpoint['img_w'],checkpoint['img_h'])

def read_crop(reader,image):
    import torch
    import numpy as np
    model,chars,size=reader
    pixels=np.array(image.convert('RGB').resize(size),dtype=np.float32)/255.
    x=torch.from_numpy(pixels).permute(2,0,1).unsqueeze(0)
    normalization=os.getenv('ANPR_OCR_NORMALIZATION','half')
    if normalization=='half':x=(x-.5)/.5
    elif normalization=='imagenet':
        x=(x-torch.tensor([.485,.456,.406])[None,:,None,None])/torch.tensor([.229,.224,.225])[None,:,None,None]
    elif normalization!='unit':raise ValueError('Unknown OCR normalization')
    with torch.inference_mode():
        scores,indices=model(x).softmax(-1)[0].max(-1)
    text=[];confidences=[];previous=-1
    for index,score in zip(indices.tolist(),scores.tolist()):
        if index!=previous and index>0:
            text.append(chars[index-1]);confidences.append(score)
        previous=index
    return ''.join(text),min(confidences,default=0.)
