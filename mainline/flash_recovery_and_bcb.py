#!/usr/bin/env python3
"""In ONE existing legacy-DA session:
 1) read recovery, report which known image it is (detects Android's flash_recovery restore)
 2) write IMAGE into recovery, verify readback
 3) set para BCB command = "boot-recovery" (first 32 bytes of para sector 0 only), verify
 4) finish(0) so the next power-on goes straight to recovery (Android never runs in between)
Usage: sudo -n /Users/matveysazhnov/mtkclient/.venv/bin/python -u flash_recovery_and_bcb.py IMAGE [--no-finish]
"""
import os, sys, hashlib, json, subprocess, logging, time
from pathlib import Path

H = Path('/Users/matveysazhnov'); MTK = H / 'mtkclient'
W = H / 'ASUS-Z301ML-port/mainline/recovery-readcheck'
N = 16777216
PARA = 0x04d00000
KNOWN = {
    '7a1a68b9dfc78607c2f4605cf4827aed06423654c60da2e6899713221f8a926e': 'stock recovery',
    '8834d45f6a18cc815d5c04332b8c785a1f09375cadb08cf133d081e02e1c9f56': 'stock recovery (rewritten by Android flash_recovery)',
    '7ccbb3941af88d0e50063da798445ba6e4e1e9365f138dea64a298f7563615fa': 'stock recovery SIG-STRIPPED',
    '2fddd55e02b0cba936f5247b8c1aa3e30825dbbab05b526dee3d43511fe48b08': 'linux7 tiny (clk+pstore)',
    '8a06b679c7693a0a54bfd13174636178cabc7ac36729628db49229456aba0476': 'linux7 tiny reloc k@0x40200000',
    '5cd74270c88e94f72219198440a6c13d940bf822b021a3c9cffd2e325df13810': 'linux7 tiny 1cpu',
    '4137399716f68f5a5c27ce47e13f294dfe049cb992c9973f2ca890f82a7f4b85': 'linux7 zimage64 1cpu',
    '511f6350ea7f2da3d45078465e477a4636f2842cf11c302b9a05d79e5e5a8ac2': 'linux7 zimage64 fbprobe',
    'b85c59ecdb5b5338727529c31539d8967e184ebc1e9660a618d9b87c334b3ca9': 'linux7-zimage64-fbprobe-STOCKDTB-FULL16MiB.img',
    'a4a7e617f00dc7bbd4cadd187a7f4df8d85e18617e5097ca50640521a91ceaf1': 'FAKEKERNEL-wdtoff-FULL16MiB.img',
    'f314e95ac9883335e764330f762caf16960c29fe610bf8fee97ad48b50f2ea93': 'FAKEKERNEL2-swrst-FULL16MiB.img',
    '75aac01e51a7e036e6fec9b7b6938daa5f7a32022fc5831db591e1217d883be3': 'FAKEKERNEL2-swrst-STOCKRAMDISK-FULL16MiB.img',
    '17fbefd6ad7aca43210c108304451ab0f4225040b1c6613a8a34cf7c0c6673f0': 'S1-stockkernel-swrst-FULL16MiB.img',
    'e2a9f9765a60b74c63ba2ca115995664973af58adfe49b8e6517294db4e7bbae': 'S2-FULL16MiB.img',
    'd9e20dfd5a3ee6791e2b9852a9504d36b5f5021d20637d1b64a6c1e045cc13c1': 'S3-FULL16MiB.img',
    'a832b3805d8b35f6708103cf608c18e9945fc634138b36b1b78b2623b41d6e04': 'L7-zimg-fbprobe-PADDED-ourdtb-FULL16MiB.img',
    'd5676f09185a8a0304de928719a79b535331bb92aeb51c35dd353420ccceedc4': 'S4-FULL16MiB.img',
    '42686021c2fb9ad02b6f7dff36d32e01c60e53329d80604a00252765f3b9d43b': 'L7-v5dtb-PADDED-FULL16MiB.img',
    'cd1693fc70aa094bbab8e1948663a682e39c6932afc21eacdcadac20e5d5f5ad': 'L7-v5dtb-fbprobe2-PADDED-FULL16MiB.img',
    '68fa750e24550abff9b99cc0d43420632295b85037b6a44c064e9b0baea17293': 'L7-v6-fbprobe3-PADDED-FULL16MiB.img',
    'd33b9e6fa3b348910acf3a783d1513bb1a72be249f4e5c11f7647c87e7f870dd': 'L7-v6-wdtlog-FULL16MiB.img',
    '9dc610c5c39604a134192e950f353671aee43671225d2da90cbd084723d51993': 'L7-v7-FULL16MiB.img',
    '2d8c7bd56e9be8a5110a177facb7d08c323b80268df7d1425e38d2f352dbbcc2': 'L7-v8-FULL16MiB.img',
    '0b908ca936345a91dad54d8f91e4f766237127363877405411c225e51a002d76': 'L7-v8-usbshell-FULL16MiB.img',
    '046a94d293f2bd20df00f6dcd307927e0a89e2ee8c8ce794a96efd9f15732694': 'L7-v9-smp-FULL16MiB.img',
    '1fa4e21d1bb060459bdb763889d33488fb489d53c9ff9c32f3f516149a79ec15': 'L7-v10-smp4-FULL16MiB.img',
    'b32ca411d7d24e5c1cc36473b9030ad17e69efa4c2f6e2dc37b5532282240faf': 'L7-v11-touch-FULL16MiB.img',
    '6b35554f53bf3033b166d4f3feda2528664d31159516db4a71a3b3a81134a59a': 'L7-v11b-FULL16MiB.img',
    '4f7b82587ab911ed18a025686bb8ff03cd073a03fa6a068530464d56639cf4e2': 'L7-v12-dsi-FULL16MiB.img',
    '77e6029aede65be96fade2f57c9432045a4252f0303430d46170fe356a8551d7': 'L7-v13-dsi-noiommu-FULL16MiB.img',
    'ba1943a6a1b748f6d4be7d316e4c838453f6ee0a60aef481543a1b05a2f51952': 'L7-v14-dsi-dison-FULL16MiB.img',
    '137e2b8be387294bea7335016168bceba005e812f7eece12f4fe7d672a356448': 'L7-v15-dsi-noreset-FULL16MiB.img',
    '52562a47d0fd26b4064e37d8b66f224a4c850ccd4974d6fe800bafae9a44c9ad': 'L7-v16-fbdev-FULL16MiB.img',
    'e2823e793614558f0570ad41fd0e4ed89c330a969b2cde7691448a85153f439d': 'L7-v17-charger-FULL16MiB.img',
    '7f1ed73699df2059add9388265ffd62437e2bb72ad85a9e2d3f69758f7648069': 'L7-v18-battery-FULL16MiB.img',
    'b0355e1ef2924fd588fb9ca279d5bb5932256222645d946aa209f5e485741fa4': 'L7-v19-cpufreq-FULL16MiB.img',
    '85047cf75f680b41b674f63d56c9978e380ed9cc18d75f154018ae365ff4c365': 'L7-v20-schedutil-FULL16MiB.img',
    'f94bd4afaa5580906b21012d5ac80db0d7f50064cbf1b44b0e1e6561a4b97f1d': 'L7-v21-thermal-FULL16MiB.img',
    '61240d89e4783986a5903e99644eed617533d8a0eac15bb83fe8ab5df509a56a': 'L7-v22-androidcfg-FULL16MiB.img',
    '84b89d3f5aafe4ba17f03cb976ceb919f1e0b58d4f785428ed38b7bd59e80cdc': 'A1-android-boot-FULL16MiB.img',
    '0003b569e0b0f5fc1392dea61741d094fe1eb5ccb1aa7f2d96a5ffdb2a9a4d58': 'A2-android-boot-FULL16MiB.img',
    'f275fe122259541ff0f3a036ebca4299d677841e3f03579eabf6899f8b6e8a5c': 'A3-android-boot-FULL16MiB.img',
    'f063363a337400e48e5f0ca2816f717c4cd510b7ad10ab12a9261a525919778c': 'A4-android-boot-FULL16MiB.img',
    '39f576f000704c9593e9ce63f69052023756f6a7448d99eefdea9788f09b9e35': 'A5-android-boot-FULL16MiB.img',
    '05719884cb65577d7dea3098866379590526bb850d3981b9e71227d3ca9375cd': 'A6-android-boot-FULL16MiB.img',
    '471dac835b19adeaec709896bed29d20be0abeaf742f0ffa803b0aeae427d035': 'S1-oneshot-sound-FULL16MiB.img',
    '25e9ce134ee81b5458963c073b6496ca1b11647cacbac63066d70f0f84f11315': 'A7-android-boot-FULL16MiB.img',
    '95063b3da276224cfcdd25ade43f2c309e2ba76d8866574f0f5bb47237058a3f': 'S2-oneshot-sound-FULL16MiB.img',
    'cef3dce86edbfba55e9fa33a85f9847d28b30cff3c974e2c138079fa3a8533f9': 'A8-android-boot-FULL16MiB.img',
    'fe4ef8fb3bdfc6dab9e3412be892ac657013dc053c996d3f4b9125f546cb0ec9': 'S3-oneshot-sndmod-FULL16MiB.img',
    '90465f5b07ae282c67b8e519264e72d47d799ba90e94eedb26c38ee7fb5f14dc': 'A9-android-boot-FULL16MiB.img',
    'feeca7cb3f14dae1f349e1627c6bce3a25b723032dca0594216b772c4cfbc3c2': 'S4-oneshot-sndmod-FULL16MiB.img',
    '91297fc49db3043466db9b57e5b26353cdcc1f460118ebe7d9834b0ff857fb65': 'A11-android-boot-FULL16MiB.img',
    '87f49419b2dd41f1cab18da9cd1e2f6ff88800e6381dde69deb20b1af61b5dfb': 'A12-android-boot-FULL16MiB.img',
    '7176931831f6137c29129b911d96a0ae0d1af9daa0bd86d9ba1ae3304035b466': 'A13-android-boot-FULL16MiB.img',
    'c8504264684df865316ce8ca09ab071034fd34d4d23bbd13774e4a1b86cb6d20': 'A14-android-boot-FULL16MiB.img',
    'dea9c7fbd44464f494838af3ec875c8be227c6a67fbae844032ed1a40d1a16d8': 'A15-android-boot-FULL16MiB.img',
    '01c36c73f8e3b01d512cfc46b8763d0c728f837a4afc36478b4ff1a356be065c': 'A16-android-boot-FULL16MiB.img',
    '13e8c78f777a7b6f0a142468bfccdac50a15bbe6a7ffdc6080c67fcb9dd7f300': 'A17-android-boot-FULL16MiB.img',
    '3d586ee8bd250c294b32a6b7fe665a071c5a8ffd4e637ca387ab4e6164a539ac': 'S5-oneshot-connsys-FULL16MiB.img',
    '1abd02aca13e10aef252dac4aa97d83d24dbcd1a9bd5cc3aa4f5b05ee3cb3359': 'A18-android-boot-FULL16MiB.img',
    '5b71f0b63bfcee9b279584284a8847130a60773b4137669d0aa02eb1a874bcc8': 'S5-oneshot-connsys-FULL16MiB.img',
    'ee0b6d7c2e9eece0f281e0cd2ed600870915c51c576503af78da2525f5110529': 'S6-oneshot-connsys-FULL16MiB.img',
    '9e34f6b872585c0ab23c27e32802a25bb7fa26633c8351aa7d0d060d7012ff5f': 'S7-oneshot-FULL16MiB.img',
    '8073a6aa78f60b9c80e097ac33125cc9150c93ef7428816ffd76155969e4f05c': 'S8-oneshot-FULL16MiB.img',
    '6164328aa66528b2b19d54fb2ebe525c70fb9299c246f83a94d2e0ffa3bb48db': 'A18-android-boot-FULL16MiB.img',
    'eee7cf9355ec0b4122bc908e54a2363ba2ac5d40d510fd0020923e5602cac015': 'S9-oneshot-FULL16MiB.img',
    'fbd85ce964e63604b04adb6253aa33345388850f1ce215f3e88c0dd69457ca19': 'S10-oneshot-FULL16MiB.img',
    '30e804f93d40493658063fdf2c52c2ac08bf7cd9f75308601b3724806ff3271f': 'S11-oneshot-FULL16MiB.img',
    'f3e54e80eb2e53f4e886a110bfeb2c430f010fdf585a5b379cd2532fe26492d1': 'S12-oneshot-FULL16MiB.img',
    'd87ff8fd9649e0a707b48d636deb3f3ed20f83ec36db3a6608c3e8db81d5eb7c': 'S13-oneshot-FULL16MiB.img',
    '818379b74f485d2c02e4b3942480cef752d0f77c77d76b32d1428f79f660103e': 'S14-oneshot-FULL16MiB.img',
    '12383cf000e38e5cc09228949a199c2f7dfdd453d329dfc76824380732bf6f76': 'A19-android-boot-FULL16MiB.img',
    '20eedf9f10844cd7113c4abf5c93f342c2c2f4d4cce4578c9c146e4e561063c5': 'S15-oneshot-FULL16MiB.img',
    '3f49ed6e60ec8dabd8b32acf3af9d0da1fc3b9bdd5ccdda12dfeabdee1621e6d': 'S15-oneshot-FULL16MiB.img',
    '61535366f87466153702ab494294ee10b6aec9d7e79359febf978d088306185b': 'A20-android-boot-FULL16MiB.img',
    '33262474b12e34dc984ba807b99f0539570e22bd4bb3bf63af9035b91b06a113': 'S16-oneshot-FULL16MiB.img',
    '0df0c97c5258de1507d057351a57536e9380c57e19a4b309b065906b8f9672d1': 'check.img',
    'db7a716a3d32e7bef025474a43bc18db64ad7ddb516726beaad4624458708f1d': 'A21-android-boot-FULL16MiB.img',
    'ca84e4e47a68682e71ff2a76f40fac0277c43622250a0daffc747da718782ee6': 'A22-android-boot-FULL16MiB.img',
    'fee65485301574199b70656e3d3264a05ff1004c81285e73d1813bc22c5a30a5': 'A23-android-boot-FULL16MiB.img',
    '9cda04b6aea7207cc0285363337c4a23117ccf3e1a55be520ae9b29dc3524279': 'A24-android-boot-FULL16MiB.img',
    '1aa551da447d52acb6c389ec14fc43d0393f030f4a358dcb890b99f3fdcd226f': 'A25-android-boot-FULL16MiB.img',
    '9761a43e241eb23020ff7be6c34e4c176abd0621465c4b6247796f5943a244b1': 'A26-android-boot-FULL16MiB.img',
    '49697b20c342034363d02e7ea12accb100a25731d09e5a8082d8f3daf80fa4dc': 'A27-android-boot-FULL16MiB.img',
    '90da7b82cff772372a7216ed951fa71931d3bb7ee691cb426f8b9fc9cd997bfd': 'A28-android-boot-FULL16MiB.img',
    '0bba4bd19dc92ef04bcb61851838ab191414e80491330b3c489b7649deeadd5b': 'A29-android-boot-FULL16MiB.img',
    '72bbca775d3f4933b7599fe2029bcf66a349476552c210e7500c4e66433696b5': 'A30-android-boot-FULL16MiB.img',
    '5e80d17557130432a50ae60b6ce353205f68bce1547d5d355f02b555255faa0d': 'A31-android-boot-FULL16MiB.img',
    'ba8a26e66750c7607bbfbe951b9d811062a4a4d1fe57ca8cfc15c08bf304f757': 'A32-android-boot-FULL16MiB.img',
    'ce0d423145104b8ca32f0fdf623e78e7fad79a36fae12c0594157a5199b4c529': 'A33-android-boot-FULL16MiB.img',
    '3ea00d334356c824c092ac2697f828711f3737d09f200df6a839d558d09c7bba': 'A34-android-boot-FULL16MiB.img',
    '701928bbce115842598c62441edc057c6356020012fd761af0033fbd007c93b2': 'A35-android-boot-FULL16MiB.img',
    'aebf9f518d0e9124dacddfe1091242232c3126c9ef32d012a21b3213fe5b8b06': 'A36-android-boot-FULL16MiB.img',
    '718e9b236370aba7f16793c83561d8c1cba00e3d93a0cffe075aa192931dfa2e': 'A37-android-boot-FULL16MiB.img',
    '617a9ce7e3fa6b60f5355ce0738ca7c193b85fcce88997326069016ddbd398b9': 'A38-android-boot-FULL16MiB.img',
    '31a4e3c4d75d9106ee7f99fc8b98a809dd24d38825abf8cee1b0df2f010ff38f': 'A39-android-boot-FULL16MiB.img',
    'f7565468fb76137e602562c6f4cf7c886af4334eac0e3bd7f79a0ab58c4eaedd': 'A40-android-boot-FULL16MiB.img',
    '50f1dd4ffb32766021a1fcbfcbe5e13134b97ec38e07e44c7331ab3599a0b799': 'A41-android-boot-FULL16MiB.img',
    'e6aa7eacdd4395be761f86ef91aa94e366e36ba525a2d048212c06f44ab9c6f2': 'test 3.18.35 (gcc15)',
    '3b260803465d1ab886bdccd1f27fecb757cef02a2ffc91d5741fc78a61f84959': 'linux7 v2 gadget',
}
CMD = b'boot-recovery'.ljust(32, b'\0')


def ck(v, m):
    if not v:
        raise RuntimeError('SAFETY STOP: ' + m)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    img = Path(sys.argv[1]).resolve()
    ck(img.is_file() and img.stat().st_size == N and img.read_bytes()[:8] == b'ANDROID!', 'bad image')
    want = sha(img)
    print('IMAGE', img.name, want[:16], KNOWN.get(want, 'NEW'), flush=True)
    s = json.loads((MTK / '.state').read_text())
    ck(s.get('hwcode') == 0x321 and s.get('meid') == 'e38fd44f882d91c96dfa77e29b2cc032', 'state')
    u = subprocess.run(['ioreg', '-p', 'IOUSB', '-l', '-w0'], capture_output=True, text=True, timeout=8).stdout
    ck('"idVendor" = 3725' in u and '"idProduct" = 8193' in u, 'DA 0e8d:2001 not present')
    ck(os.geteuid() == 0, 'sudo')
    ts = time.strftime('%H%M%S')
    pre, post = W / f'recovery-pre-{ts}.bin', W / f'recovery-post-{ts}.bin'
    psec, psec_new, psec_post = W / f'para-s0-pre-{ts}.bin', W / f'para-s0-new-{ts}.bin', W / f'para-s0-post-{ts}.bin'
    os.chdir(MTK); sys.path.insert(0, str(MTK)); sys.modules['mfusepy'] = None
    from mtkclient.config.mtk_config import MtkConfig
    from mtkclient.Library.mtk_class import Mtk
    from mtkclient.Library.DA.mtk_da_handler import DaHandler
    from mtkclient.Library.Partitions.gpt import GptSettings
    cfg = MtkConfig(loglevel=logging.INFO); cfg.gpt_settings = GptSettings(0, 0, 0)
    mtk = Mtk(config=cfg, loglevel=logging.INFO); da = DaHandler(mtk, logging.INFO)
    mtk = da.connect(mtk, directory='.'); ck(mtk is not None and mtk.reinited, 'DA resume')
    mtk = da.configure_da(mtk); ck(mtk.daloader.patch and mtk.config.hwcode == 0x321, 'DA')
    ok, part = mtk.daloader.detect_partition('recovery', parttype='user')
    ck(ok and part.sector == 191488 and part.sectors == 32768, 'recovery GPT')
    addr = part.sector * 512
    ok, pp = mtk.daloader.detect_partition('para', parttype='user')
    ck(ok and pp.sector * 512 == PARA, 'para GPT')

    ck(mtk.daloader.readflash(addr=addr, length=N, filename=str(pre), parttype='user'), 'pre-read')
    cur = sha(pre)
    print('CURRENT RECOVERY', cur[:16], KNOWN.get(cur, 'UNKNOWN'), flush=True)
    ck(cur in KNOWN, 'unknown recovery content; refuse')
    if cur != want:
        print('WRITING recovery', flush=True)
        ck(mtk.daloader.writeflash(addr=addr, length=N, filename=str(img), parttype='user'), 'write')
        ck(mtk.daloader.readflash(addr=addr, length=N, filename=str(post), parttype='user'), 'post-read')
        ck(sha(post) == want, 'RECOVERY READBACK MISMATCH')
    print('RECOVERY OK =', img.name, flush=True)

    ck(mtk.daloader.readflash(addr=PARA, length=512, filename=str(psec), parttype='user'), 'para read')
    s0 = psec.read_bytes()
    print('PARA BCB BEFORE', s0[:32], flush=True)
    ck(s0[:32] in (bytes(32), CMD), 'unexpected BCB content; refuse')
    if s0[:32] != CMD:
        psec_new.write_bytes(CMD + s0[32:])
        ck(mtk.daloader.writeflash(addr=PARA, length=512, filename=str(psec_new), parttype='user'), 'para write')
    ck(mtk.daloader.readflash(addr=PARA, length=512, filename=str(psec_post), parttype='user'), 'para post-read')
    ck(psec_post.read_bytes() == CMD + s0[32:], 'BCB READBACK MISMATCH')
    print('PARA BCB = boot-recovery (verified)', flush=True)

    if '--no-finish' in sys.argv:
        print('Staying in DA'); return
    print('FINISH(0) ACK:', mtk.daloader.da.finish(0), flush=True)
    try:
        mtk.port.close(reset=True)
    except Exception as e:
        print('close/reset:', repr(e))


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print('STOPPED:', repr(e), flush=True); sys.exit(1)
