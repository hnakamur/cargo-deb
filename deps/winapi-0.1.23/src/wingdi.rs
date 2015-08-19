// Copyright © 2015, Peter Atashian
// Licensed under the MIT License <LICENSE.md>
//! GDI procedure declarations, constant definitions and macros
//83
pub const SRCCOPY: ::DWORD = 0x00CC0020;
pub const SRCPAINT: ::DWORD = 0x00EE0086;
pub const SRCAND: ::DWORD = 0x008800C6;
pub const SRCINVERT: ::DWORD = 0x00660046;
pub const SRCERASE: ::DWORD = 0x00440328;
pub const NOTSRCCOPY: ::DWORD = 0x00330008;
pub const NOTSRCERASE: ::DWORD = 0x001100A6;
pub const MERGECOPY: ::DWORD = 0x00C000CA;
pub const MERGEPAINT: ::DWORD = 0x00BB0226;
pub const PATCOPY: ::DWORD = 0x00F00021;
pub const PATPAINT: ::DWORD = 0x00FB0A09;
pub const PATINVERT: ::DWORD = 0x005A0049;
pub const DSTINVERT: ::DWORD = 0x00550009;
pub const BLACKNESS: ::DWORD = 0x00000042;
pub const WHITENESS: ::DWORD = 0x00FF0062;
//121
// fnCombineMode values for CombineRgn
pub const RGN_AND: ::c_int = 1;
pub const RGN_OR: ::c_int = 2;
pub const RGN_XOR: ::c_int = 3;
pub const RGN_DIFF: ::c_int = 4;
pub const RGN_COPY: ::c_int = 5;
pub const RGN_MIN: ::c_int = RGN_AND;
pub const RGN_MAX: ::c_int = RGN_COPY;
//572 (Win 7 SDK)
#[repr(C)] #[derive(Clone, Copy, Debug)]
pub struct BITMAP {
    pub bmType: ::LONG,
    pub bmWidth: ::LONG,
    pub bmHeight: ::LONG,
    pub bmWidthBytes: ::LONG,
    pub bmPlanes: ::WORD,
    pub bmBitsPixel: ::WORD,
    pub bmBits: ::LPVOID,
}
pub type PBITMAP = *mut BITMAP;
pub type NPBITMAP = *mut BITMAP;
pub type LPBITMAP = *mut BITMAP;
#[repr(C)] #[derive(Clone, Copy, Debug)]
pub struct RGBQUAD {
    pub rgbBlue: ::BYTE,
    pub rgbGreen: ::BYTE,
    pub rgbRed: ::BYTE,
    pub rgbReserved: ::BYTE,
}
pub type LPRGBQUAD = *mut RGBQUAD;
pub const CS_ENABLE: ::DWORD = 0x00000001;
pub const CS_DISABLE: ::DWORD = 0x00000002;
pub const CS_DELETE_TRANSFORM: ::DWORD = 0x00000003;
pub const LCS_SIGNATURE: ::DWORD = 0x5053_4F43; // 'PSOC'
pub const LCS_sRGB: LCSCSTYPE = 0x7352_4742; // 'sRGB'
pub const LCS_WINDOWS_COLOR_SPACE: LCSCSTYPE = 0x5769_6E20; // 'Win '
pub type LCSCSTYPE = ::LONG;
pub const LCS_CALIBRATED_RGB: LCSCSTYPE = 0x00000000;
pub type LCSGAMUTMATCH = ::LONG;
pub const LCS_GM_BUSINESS: LCSGAMUTMATCH = 0x00000001;
pub const LCS_GM_GRAPHICS: LCSGAMUTMATCH = 0x00000002;
pub const LCS_GM_IMAGES: LCSGAMUTMATCH = 0x00000004;
pub const LCS_GM_ABS_COLORIMETRIC: LCSGAMUTMATCH = 0x00000008;
pub const CM_OUT_OF_GAMUT: ::BYTE = 255;
pub const CM_IN_GAMUT: ::BYTE = 0;
pub const ICM_ADDPROFILE: ::UINT = 1;
pub const ICM_DELETEPROFILE: ::UINT = 2;
pub const ICM_QUERYPROFILE: ::UINT = 3;
pub const ICM_SETDEFAULTPROFILE: ::UINT = 4;
pub const ICM_REGISTERICMATCHER: ::UINT = 5;
pub const ICM_UNREGISTERICMATCHER: ::UINT = 6;
pub const ICM_QUERYMATCH: ::UINT = 7;
pub type FXPT16DOT16 = ::c_long;
pub type LPFXPT16DOT16 = *mut ::c_long;
pub type FXPT2DOT30 = ::c_long;
pub type LPFXPT2DOT30 = *mut ::c_long;
#[repr(C)] #[derive(Clone, Copy, Debug)]
pub struct CIEXYZ {
    pub ciexyzX: FXPT2DOT30,
    pub ciexyzY: FXPT2DOT30,
    pub ciexyzZ: FXPT2DOT30,
}
pub type LPCIEXYZ = *mut CIEXYZ;
#[repr(C)] #[derive(Clone, Copy, Debug)]
pub struct CIEXYZTRIPLE {
    pub ciexyzRed: CIEXYZ,
    pub ciexyzGreen: CIEXYZ,
    pub ciexyzBlue: CIEXYZ,
}
pub type LPCIEXYZTRIPLE = *mut CIEXYZTRIPLE;
//716 (Win 7 SDK)
#[repr(C)] #[derive(Clone, Copy, Debug)]
pub struct BITMAPINFOHEADER {
    pub biSize: ::DWORD,
    pub biWidth: ::LONG,
    pub biHeight: ::LONG,
    pub biPlanes: ::WORD,
    pub biBitCount: ::WORD,
    pub biCompression: ::DWORD,
    pub biSizeImage: ::DWORD,
    pub biXPelsPerMeter: ::LONG,
    pub biYPelsPerMeter: ::LONG,
    pub biClrUsed: ::DWORD,
    pub biClrImportant: ::DWORD,
}
pub type LPBITMAPINFOHEADER = *mut BITMAPINFOHEADER;
pub type PBITMAPINFOHEADER = *mut BITMAPINFOHEADER;
#[repr(C)] #[derive(Clone, Copy, Debug)]
pub struct BITMAPV5HEADER {
    pub bV5Size: ::DWORD,
    pub bV5Width: ::LONG,
    pub bV5Height: ::LONG,
    pub bV5Planes: ::WORD,
    pub bV5BitCount: ::WORD,
    pub bV5Compression: ::DWORD,
    pub bV5SizeImage: ::DWORD,
    pub bV5XPelsPerMeter: ::LONG,
    pub bV5YPelsPerMeter: ::LONG,
    pub bV5ClrUsed: ::DWORD,
    pub bV5ClrImportant: ::DWORD,
    pub bV5RedMask: ::DWORD,
    pub bV5GreenMask: ::DWORD,
    pub bV5BlueMask: ::DWORD,
    pub bV5AlphaMask: ::DWORD,
    pub bV5CSType: ::LONG, // LONG to match LOGCOLORSPACE
    pub bV5Endpoints: CIEXYZTRIPLE,
    pub bV5GammaRed: ::DWORD,
    pub bV5GammaGreen: ::DWORD,
    pub bV5GammaBlue: ::DWORD,
    pub bV5Intent: ::LONG, // LONG to match LOGCOLORSPACE
    pub bV5ProfileData: ::DWORD,
    pub bV5ProfileSize: ::DWORD,
    pub bV5Reserved: ::DWORD,
}
pub type LPBITMAPV5HEADER = *mut BITMAPV5HEADER;
pub type PBITMAPV5HEADER = *mut BITMAPV5HEADER;
pub const PROFILE_LINKED: ::LONG = 0x4C49_4E4B; // 'LINK'
pub const PROFILE_EMBEDDED: ::LONG = 0x4D42_4544; // 'MBED'
pub const BI_RGB: ::DWORD = 0;
pub const BI_RLE8: ::DWORD = 1;
pub const BI_RLE4: ::DWORD = 2;
pub const BI_BITFIELDS: ::DWORD = 3;
pub const BI_JPEG: ::DWORD = 4;
pub const BI_PNG: ::DWORD = 5;
#[repr(C)] #[derive(Debug)] #[allow(missing_copy_implementations)]
pub struct BITMAPINFO {
    pub bmiHeader: BITMAPINFOHEADER,
    pub bmiColors: [RGBQUAD; 0],
}
pub type LPBITMAPINFO = *mut BITMAPINFO;
pub type PBITMAPINFO = *mut BITMAPINFO;
//1438
pub const LF_FACESIZE: usize = 32;

#[repr(C)] #[derive(Copy, Clone)]
pub struct LOGFONTA {
    pub lfHeight: ::LONG,
    pub lfWidth: ::LONG,
    pub lfEscapement: ::LONG,
    pub lfOrientation: ::LONG,
    pub lfWeight: ::LONG,
    pub lfItalic: ::BYTE,
    pub lfUnderline: ::BYTE,
    pub lfStrikeOut: ::BYTE,
    pub lfCharSet: ::BYTE,
    pub lfOutPrecision: ::BYTE,
    pub lfClipPrecision: ::BYTE,
    pub lfQuality: ::BYTE,
    pub lfPitchAndFamily: ::BYTE,
    pub lfFaceName: [::CHAR; LF_FACESIZE],
}
pub type LPLOGFONTA = *mut LOGFONTA;

#[repr(C)] #[derive(Copy, Clone)]
pub struct LOGFONTW {
    pub lfHeight: ::LONG,
    pub lfWidth: ::LONG,
    pub lfEscapement: ::LONG,
    pub lfOrientation: ::LONG,
    pub lfWeight: ::LONG,
    pub lfItalic: ::BYTE,
    pub lfUnderline: ::BYTE,
    pub lfStrikeOut: ::BYTE,
    pub lfCharSet: ::BYTE,
    pub lfOutPrecision: ::BYTE,
    pub lfClipPrecision: ::BYTE,
    pub lfQuality: ::BYTE,
    pub lfPitchAndFamily: ::BYTE,
    pub lfFaceName: [::WCHAR; LF_FACESIZE],
}
pub type LPLOGFONTW = *mut LOGFONTW;

//1595
#[inline]
pub fn RGB (r: ::BYTE, g: ::BYTE, b: ::BYTE) -> ::COLORREF {
  r as ::COLORREF | ((g as ::COLORREF) << 8) | ((b as ::COLORREF) << 16)
}
//1906 (Win 7 SDK)
pub const DIB_RGB_COLORS: ::UINT = 0;
pub const DIB_PAL_COLORS: ::UINT = 1;

#[repr(C)] #[derive(Clone, Copy, Debug)]
pub struct RGNDATAHEADER {
    pub dwSize: ::DWORD,
    pub iType: ::DWORD,
    pub nCount: ::DWORD,
    pub nRgnSize: ::DWORD,
    pub rcBound: ::RECT,
}
pub type PRGNDATAHEADER = *mut RGNDATAHEADER;
#[repr(C)] #[derive(Debug)] #[allow(missing_copy_implementations)]
pub struct RGNDATA {
    pub rdh: RGNDATAHEADER,
    pub Buffer: [::c_char; 0],
}
pub type PRGNDATA = *mut RGNDATA;
pub type NPRGNDATA = *mut RGNDATA;
pub type LPRGNDATA = *mut RGNDATA;
#[repr(C)] #[derive(Clone, Copy, Debug)]
pub struct PALETTEENTRY {
    pub peRed: ::BYTE,
    pub peGreen: ::BYTE,
    pub peBlue: ::BYTE,
    pub peFlags: ::BYTE
}

//3581
pub type LINEDDAPROC = Option<unsafe extern "system" fn(::c_int, ::c_int, ::LPARAM)>;

pub const COINIT_APARTMENTTHREADED: ::DWORD = 0x2;
pub const COINIT_MULTITHREADED: ::DWORD = 0x0;
pub const COINIT_DISABLE_OLE1DDE: ::DWORD = 0x4;
pub const COINIT_SPEED_OVER_MEMORY: ::DWORD = 0x8;
