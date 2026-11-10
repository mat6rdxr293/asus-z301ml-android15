#!/usr/bin/env python3
"""Exit existing legacy DA with finish(0) NORMAL. No eMMC writes."""
import os,sys,logging
from pathlib import Path
MTK=Path('/Users/matveysazhnov/mtkclient')
assert os.geteuid()==0
os.chdir(MTK);sys.path.insert(0,str(MTK));sys.modules['mfusepy']=None
from mtkclient.config.mtk_config import MtkConfig
from mtkclient.Library.mtk_class import Mtk
from mtkclient.Library.DA.mtk_da_handler import DaHandler
from mtkclient.Library.Partitions.gpt import GptSettings
cfg=MtkConfig(loglevel=logging.INFO);cfg.gpt_settings=GptSettings(0,0,0)
mtk=Mtk(config=cfg,loglevel=logging.INFO);da=DaHandler(mtk,logging.INFO)
mtk=da.connect(mtk,directory='.');assert mtk is not None and mtk.reinited
mtk=da.configure_da(mtk);assert mtk.daloader.patch and mtk.config.hwcode==0x321
print('FINISH(0) ACK:',mtk.daloader.da.finish(0),flush=True)
try:mtk.port.close(reset=True)
except Exception as e:print('close/reset:',repr(e),flush=True)
