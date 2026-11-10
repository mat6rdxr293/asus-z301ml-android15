#!/usr/bin/env python3
"""Read expdb (LK kedump incl. pstore console window) from an existing legacy DA session."""
import os,sys,logging
from pathlib import Path
MTK=Path('/Users/matveysazhnov/mtkclient'); out=Path(sys.argv[1]).resolve()
assert os.geteuid()==0
os.chdir(MTK); sys.path.insert(0,str(MTK)); sys.modules['mfusepy']=None
from mtkclient.config.mtk_config import MtkConfig
from mtkclient.Library.mtk_class import Mtk
from mtkclient.Library.DA.mtk_da_handler import DaHandler
from mtkclient.Library.Partitions.gpt import GptSettings
cfg=MtkConfig(loglevel=logging.INFO); cfg.gpt_settings=GptSettings(0,0,0)
mtk=Mtk(config=cfg,loglevel=logging.INFO); da=DaHandler(mtk,logging.INFO)
mtk=da.connect(mtk,directory='.'); assert mtk is not None and mtk.reinited
mtk=da.configure_da(mtk)
ok,part=mtk.daloader.detect_partition('expdb',parttype='user'); assert ok
assert mtk.daloader.readflash(addr=part.sector*512,length=part.sectors*512,filename=str(out),parttype='user')
print('EXPDB READ', out, out.stat().st_size)
