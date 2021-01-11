/*
 * Chapter codes are a six-digit number stored as a string.
 *
 * The first digit is the season number.  It is a 1 for series without seasons.
 *
 * The next four digits are the chapter number.  This allows for a maximum of 9999 chapters.
 * A 4-digit chapter number is required as there exist series with >1000 chapters,
 * such as Hajime no Ippo.
 *
 * The last digit is the decimal, for extra chapters/omake/etc.  These are usually marked
 * as e.g. chapter 23.5, but may be other numbering systems such as .1 -> .2 -> .3
 * or .5 -> .7 -> .9 for series with frequent non-numbered chapters.
 */
vm.ChapterDisplay=function(e)
{
    var t = parseInt(e.slice(1, -1));
    var n = e[e.length - 1];
    return 0 == n ? t : t + "." + n;
}

vm.PageOne = "-page-1";
vm.ChapterURLEncode=function(e)
{
    Index="";
    var t = e.substring(0, 1);
    1 != t && (Index = "-index-" + t);
    var n = parseInt(e.slice(1, -1));
    var m = "",
    var a = e[e.length - 1];
    return 0 != a && (m = "." +a ), "-chapter-" + n + m + Index + vm.PageOne + ".html"
}
