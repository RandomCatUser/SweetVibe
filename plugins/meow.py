"""
PLUGIN :: MEOW EASTER EGG (v3)
==============================
Type :meow in the command bar to summon the classic shady dancing
cat ASCII animation (12 frames, embedded - fully offline).

  :meow        -> open the dance
  :meow fast   -> faster
  :meow slow   -> slower

Drawn clamped inside its box with only asciimatics basic colours
(0-7), so it can never crash the renderer.
"""

import time as _time

_player = None

_ST = {"mode": "none", "frame": 0, "last": 0.0, "interval": 0.1}

# From http://www.qqpr.com/ascii/js/1051.js (12-frame dancing cat),
# embedded here so the plugin works fully offline. Frames are head-aligned
# and padded to a uniform canvas so the dance stays upright.
_F = [

    [
        '                               ,:                           ',
        '                              :BBN:                         ',
        '                            .rBU:LB5r.                      ',
        '                         r5BqU:    :UB8r                    ',
        '                       LMqi.          :rG8,             .:  ',
        '                     rMX                 7GL:i:i        uBY ',
        '                   .BF          iUXjNuUi   8M;;2B2.      0: ',
        '                  iBi          ZBS   .;B:  1Y    iOP        ',
        '               UMMB.          BY   7SSj;    Jv.    GO    ,  ',
        '               rBB.          MU  XG1,   .:.  .BL    :E   UB:',
        '                Bj           8u7BJ      ;  i.,1B,    B:   BB',
        '                B            ,:        .:,i, 7BU    F2   :B ',
        '          .     B    .77r,                    BB.    UU    .',
        '         78:    B7 iMB;.:BY 7BBBB0v          :B;     B.     ',
        '    .v          7M.B.  rFu  kBBBBBBBr       .Bi     UB    7B',
        '   LBM           BBB .BX     BBBMMPSNB     :B;      :2Mj  MZ',
        '        . ,...,   MMUBJ       LBBBP rB    YBr          YB8B ',
        '      ,.....            ::..    vMBZF:   BB.            .Ei ',
        ': ...                      .. .        :Z7     ...,.,..     ',
        '                                    .  ..  . ,              ',
    ],
    [
        '                                .BBj                        ',
        '                             .,LBNiMB.                      ',
        '                         iPM081Ur   7Mq7              .7r   ',
        '                      .jBPi.          :M8r            ,BB   ',
        '                    ,UBZ.                i8:                ',
        '                .  FU:         .i:.      .2B87i.            ',
        '               .BBBu        .uBXYr5B5. Lk;r.:;XMB:          ',
        '                BBr        :ML:.,i;uBX.Bi       ;EB.        ',
        '                BY        jM:JMP7:.:: .r0ZZ5r     uB,       ',
        '               .B         MBY7     :. :.i .1B8     LB       ',
        '               rG r22.             .r::.:    vM     Br      ',
        '               SBBUiSB.              .        B     JS      ',
        '               .B LkJ5                       XB     5Y      ',
        '                :Bj     uBBBU               :B:     FBU.    ',
        '                 Br.    iBBBBZ. .          :B,       .SBM  i',
        ' .              .i,:.. .      ....., .    YB.           UB7.',
        '....:,.,..:.:.,.                     .,,.JX              ,Bi',
        '     .                                   .  ,.,..,..,...  ..',
        '                                                            ',
        '                                                            ',
    ],
    [
        '                                Zk.                         ',
        '                            ...rBE1q.                       ',
        '                        71OqG5M8,  iE7.                     ',
        '                     :qOXY.          Y8U                    ',
        '                 v7:EE;                2Gi                  ',
        '                 BB8,                    BB                 ',
        '                ,B:            .:         BB                ',
        '               ,Bi         ,MBBBB1:        UB               ',
        '               MP        :BBB0:  .:.:,:::.  BLrGBS.         ',
        '              .B        iBMi   ,kBBBM21kFMB7LB,UBB1         ',
        '              701GBBB.  .,   1Br.          7NB:             ',
        '              YBBPk0k,       B0,,:           :B7            ',
        '               B:            .YY2Yi;UqBZi     ,BJ           ',
        '               F1   kU                 :MB,     BB          ',
        '. ..           :B  iBB8i        .        rB      GB5        ',
        '.. ..:          B:   BBi:..,.,  , ,, ,  :BBq       kB5.     ',
        '      .,.       ZB.  .:.,             .:Mi B        .7BB7   ',
        '         .,.,.,  ..                        B,          7BY..',
        '                                            ,..:..:.:       ',
        '                                                            ',
    ],
    [
        '                                  UB.                       ',
        '                          iBB:  jBSq2                       ',
        '                      ,i5SBZGZPB8: .Bi                      ',
        '                   .0Pqr:           r5B7                    ',
        '                  EB7                 :BE                   ',
        '                 BG   i.                8B                  ',
        '                MB   BBG                 qB                 ',
        '               .B    q0        1r         Bi                ',
        '               Bi 8r        .7BB,         iB                ',
        '              .B ZBr    , .5BBBj      .7M. B.XBM            ',
        '              q7iBBBBBBNrLSi ;UiBY.v2GBB1  BBB8:            ',
        '              B.BY0i::iBU7;.....GBBi. Y.  YB                ',
        '           .BBG1JrNXkMNBXLYLr7;rriiYLX,   :q1,              ',
        '........:.,.L :B  FkB7.              .      rSBU.           ',
        ' . . .        :: ki     .rLq2FNZ81Lr.  :. ..  :XGU:         ',
        '               .UBr:7UPU05vL;.. ,,,              :MOU.      ',
        '                .iL7;i..                          .i5Bi     ',
        '                                                     .:,..:.',
        '                                                            ',
        '                                                            ',
    ],
    [
        '                            7:                              ',
        '                           UBk                              ',
        '                                  SBi                       ',
        '                       :LNFUYPYYjEBBB                       ',
        '                    L2BU;:.    :   iLE7                     ',
        '                  7BB:        8BM    BBB7                   ',
        '                 BB,        iBk BF YBB ,BN                  ',
        '                BF          M7  .F 1J    Bq                 ',
        '               BZ                         B:                ',
        '        ;M    7B                          FM                ',
        '        BB;   Br                      .7  :M                ',
        '         :    B         .,           GBB.  Bi.              ',
        '       MY    ,BB7.    YMBB           XL    Br7M2            ',
        '      :BBU  .7BBBBBYJES,UB::..:U8B.       7B   B:           ',
        '      :OiU: :..     .   .LY71EUU,BMP,    iBL0GXB:    .  ,  ,',
        ' ....,                .            .   .qB.  .rqj:.: . ..  :',
        '.                     ,.             i7kG. .               .',
        '                       :.  .., ...,...                    ..',
        '                             .  .                         :.',
        '                                                           .',
    ],
    [
        '                                  i                         ',
        '                          :;7r;..BBP                        ',
        '                     iXPM051vLuFBB PBY                      ',
        '                   kBkL.        r   YqP:                    ',
        '                 iBE                   NB:                  ',
        '                2B,                     7BMSBMUi   :i       ',
        '               7B:                       :BBUj1BBS .BB      ',
        '               Bi        70r              5MX:u2r Y:        ',
        '              7B        .BjBBr             BB, rE:.MBi      ',
        '              0L        EB  :.             BXB   B. BB7     ',
        '    ,BB       Br        ,:                 Bi:   7B YBB     ',
        '     .        85                          LG.    UB  i,     ',
        '      ::   ,  7Y ,.,.,., .                BYrBOMY5.         ',
        '     7BSr.,              . ,;UL           r   7BB.   ...,.,.',
        ' ..: 7.                     :F:                 YGi. . ..   ',
        '..                      :., ,           ...,...             ',
        '                        i      .. ....,. .                  ',
        '                        . :.,.:.... .                       ',
        '                                                            ',
        '                                                            ',
    ],
    [
        '                                  2,                        ',
        '                     ,rYqkMkqPNG01BB   Y1                   ',
        '                   YZBk7  .    ,Y  FB,.BB:                  ',
        '                 qBZ,               7qBZiN8OBB8.            ',
        '                BZ                    rB, rBr kBB7          ',
        '               BB                      .BL  B,  BBi         ',
        '              G0      .:.               .Bj  B,             ',
        '             ,B       LBMBN               B. jB             ',
        '             iB       1U .i               B: rq             ',
        '             J1       YB                  BY SY             ',
        '             ;B.       Br                 Y: BM             ',
        '    FE       .BBL ,.: ..,.: .             B  .qBL           ',
        '    0B      . 7Li           .,.          XB    ,BBi....,., :',
        '        ..: .                 .,       .BB   .  .:, .       ',
        ' . ..: ..                  .   .    .uBBU. ,.:              ',
        '..                        .:. :.  ,.:Yv.                    ',
        '                           .,.,. ..                         ',
        '                                                            ',
        '                                                            ',
        '                                                            ',
    ],
    [
        '                                  :.                        ',
        '                        rrr;YSjrr2BB                        ',
        '                    iB8Xvv7Lr;v2jLqBL  ..:,.                ',
        '                 ,XBk:.            .BEMBBMB7  ,.            ',
        '                LBr                  :0BXi    EB8           ',
        '               rB.                     uBB8.                ',
        '              :B.     ZB0E7             rSUB:               ',
        '              B:      Zj 7B              .B:B               ',
        '             :B       iB                  B,Uu              ',
        '             r0        B.                 Mi B              ',
        '             rB        .                  L7 B              ',
        '             ,BB           .              5, jMU            ',
        '.             OBU ...:.:,  , , ,         :B    qB7.    .., .',
        'i           .   ...           .  .      :B:     rPu.: .     ',
        ':.,.....:.,..              .,., .:   .rNBi   :              ',
        '    . .                     . ,:.:. ;PNY.  .                ',
        '                                                            ',
        '                                                            ',
        '                                                            ',
        '                                                            ',
    ],
    [
        '                             :J                             ',
        '                      .:iLYLqBBBP                           ',
        '                   LEMBL:i::...LZG8X:                       ',
        '                 7ZN,   Ui        ,JBB;                     ',
        '               :M2     ,BNB:         ,PF                    ',
        '              JBi      UU :Bi          qB                   ',
        '             vB.       ZY   .           BU                  ',
        '             B,        .                 BO                 ',
        '            ;S                           MBB                ',
        '            Bv;:                         L1B0               ',
        '            BrBBB:.                      5OqBj              ',
        '            B  qBBBi      .........      B. :XN:            ',
        ' . ,...      Br   .i  .:.:.. .       :   NZ    .O0.    ... ,',
        ' ..   : .:  ,7r     .               .   iB       YBi... .   ',
        ':,.                             .,i:   .:., .... .,         ',
        '                                                            ',
        '                                                            ',
        '                                                            ',
        '                                                            ',
        '                                                            ',
    ],
    [
        '                             iY                             ',
        '                         MB.iBBk                            ',
        '                .u, ,XSNMBBBB7 BB57:                        ',
        '               LBBBBMP:    7:  .Bi:FqL                      ',
        '              :MBBv.                :BM                     ',
        '           .B  NB                     BB                    ',
        '           BB  B                       BM                   ',
        '          BBN Br                        B.                  ',
        '         Z8G, B  .:ii.:,                PP                  ',
        '        BB BY,S:B5XBS7rSB:              :B                  ',
        '       8B  XBUrYBXOYuu1XB.               B                  ',
        '     .MB   PZB.     .:                   Bi                 ',
        '.    EX     rB     ,: ,.r  . .  .       rBJUBSi.            ',
        '.  ,.:     .B:     rr iir,.. : .. .,.:.:P2   .iUUY.        .',
        '        ,...8: ,..,.,..                    . . ..vN:.,., ...',
        '                                                            ',
        '                                                            ',
        '                                                            ',
        '                                                            ',
        '                                                            ',
    ],
    [
        '                     8B.            YE.                     ',
        '                    2:   1v,:rvjLrBB7B                      ',
        '                        MBBBF7Yii72  XB:                    ',
        '                     LBBv.            rMBv                  ',
        '                   jBu,                 .2B:                ',
        '                  qB                      :Bi               ',
        '                 uB      .:.,              iB               ',
        '              :BBB.   :BBBBG2Si             M7              ',
        '             ;BBBS   8N      ,B:            :B     ::       ',
        '                8   :B  ,:iY7UB              B iM  vi       ',
        '                Br  :BPqPY;ir.               B  BPF,  iS    ',
        '        ,BL    .BB         ,, .,i            B iG .Lj,B7    ',
        '   .  .LBB0;JUMBBBLr2      r: vii           MBJB:   PBB5i  :',
        ',. ,.,.j, 7Y7vUBBBBi    . ..:::.. :.,.:.. ij:ZE    :BBBBPOM ',
        '              . .:r27.., ...                     . ..   ir, ',
        '                                                            ',
        '                                                            ',
        '                                                            ',
        '                                                            ',
        '                                                            ',
    ],
    [
        '                                   7.                       ',
        '                                 .BBB7                      ',
        '                            rLJSMqY vB7,                    ',
        '                        :JMMGY:.      JBN,                  ',
        '                      jMSY.             iBq         .       ',
        '                    vPv,                  ME       .BB;     ',
        '                 :BBF.                     BJ       :BB     ',
        '                 :BJ        .2BBXkEM.       BPJNSr          ',
        '                 YP        NJ:    .Bk       LB: ,NG         ',
        '                 B:       NX   :LMS7  ..     B1   Bi YB     ',
        '       :BU,BB   .B        BL:FMNL   ... ..   MB   ,B uBG    ',
        '     ,BB87 L:   :B        :ur.      :. irL   MB.   M.0,XM8.:',
        '    iBB         ,BMvM                :i.:    B8    Y7B  iUPG',
        '     .::i        B,.BBUN:                   M0     BF5     .',
        '    :5NYPMir:    MB7:JBBB57               YEU     NBEL     :',
        ' . ;U7   :rFi, ..iq:  1BBBBi       .     :Yr .  ,:7r7i ,.  L',
        '                       rv2F,. .,  ,...,                     ',
        '                                                            ',
        '                                                            ',
        '                                                            ',
    ],
]


_CAT_COLOR = 3      # yellow (basic 0-7, safe for asciimatics)
_ACCENT_COLOR = 6   # cyan (basic 0-7)


def _open(player):
    _ST.update(mode="view", frame=0, last=_time.time())
    player.add_log("Meow! (the classic dancing cat is here)")


def _on_command(cmd, raw_text):
    low = cmd.strip().lower()
    if not (low in (":meow",) or low.startswith(":meow ")):
        return False
    if _player is None:
        return True
    sub = (raw_text.split(None, 1)[1].lower() if len(raw_text.split(None, 1)) > 1
           and raw_text.split(None, 1)[1] else "")
    if sub == "fast":
        _ST["interval"] = 0.05
    elif sub == "slow":
        _ST["interval"] = 0.3
    else:
        _ST["interval"] = 0.1
    _open(_player)
    return True


def _on_key(key_str, action):
    if _ST["mode"] == "none":
        return False
    ks = (key_str or "").lower()
    if ks in ("ctrl+b", "escape", "esc", "\x1b"):
        _ST["mode"] = "none"
        return True
    return True


def _on_tick():
    if _ST["mode"] != "view":
        return
    now = _time.time()
    if now - _ST["last"] >= _ST["interval"]:
        _ST["last"] = now
        _ST["frame"] = (_ST["frame"] + 1) % len(_F)


def _draw(screen):
    if _ST["mode"] != "view":
        return
    from asciimatics.screen import Screen as Scr
    try:
        w, h = screen.width, screen.height
        fw = len(_F[0][0])
        fh = len(_F[0])
        bw = min(fw + 4, w)
        bh = min(fh + 2, h)
        bx = (w - bw) // 2
        by = (h - bh) // 2
        if _player is not None and hasattr(_player, "draw_box"):
            _player.draw_box(bx, by, bw, bh, " MEOW! ", Scr.COLOUR_YELLOW,
                             rounded=True, bg=Scr.COLOUR_BLACK)
        frame = _F[_ST["frame"]]
        start_row = 0
        avail_h = max(0, h - 2)
        if fh > avail_h:
            start_row = (fh - avail_h) // 2
        cy = by + 1
        max_w = max(0, bw - 2)
        for line in frame[start_row:start_row + avail_h]:
            line = line[:max_w]
            try:
                screen.print_at(line.rstrip(), bx + 1, cy, _CAT_COLOR, Scr.A_BOLD)
            except Exception:
                pass
            cy += 1
        if by + bh - 1 < h:
            try:
                screen.print_at("CTRL+B dismiss".center(bw - 2), bx + 1, by + bh - 1,
                                Scr.COLOUR_BLACK, Scr.A_BOLD, bg=Scr.COLOUR_YELLOW)
            except Exception:
                pass
    except Exception:
        pass


def setup(player):
    global _player
    _player = player
    player.plugin_hooks["on_command"].append(_on_command)
    player.plugin_hooks["on_draw"].append(_draw)
    player.plugin_hooks["on_key"].append(_on_key)
    player.plugin_hooks["on_tick"].append(_on_tick)
    player.add_log("Meow plugin v3 loaded (:meow - classic dancing cat)")

