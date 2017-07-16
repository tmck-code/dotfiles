" package manager
execute pathogen#infect()

" global variables to enable plugins
syntax on
filetype plugin indent on
syntax enable

" very basic editor behaviour
set number
set expandtab
set tabstop=2


" COLOURS AND
if has("termguicolors")
    set termguicolors
endif

set background=dark
set t_Co=256

colorscheme quantum

" NERDTree settings, open NERDTree by default
autocmd vimenter * if !argc() | NERDTree | endif
autocmd bufenter * if (winnr("$") == 1 && exists("b:NERDTreeType") && b:NERDTreeType == "primary") | q | endif

map <C-S-n> :NERDTreeToggle<CR>

" Disable editor mode in default bar
set noshowmode

" Detect file encoding
if has("multi_byte")
  if &termencoding == ""
    let &termencoding = &encoding
    endif
  set encoding=utf-8
  setglobal fileencoding=utf-8
  setglobal bomb
  set fileencodings=ucs-bom,utf-8,latin1
endif

" Required
set encoding=utf8

" Status bar and devicon settings
let g:airline_powerline_fonts = 1
let g:webdevicons_enable_airline_statusline = 1
let g:webdevicons_enable_airline_tabline = 1
let g:WebDevIconsNerdTreeAfterGlyphPadding = '  '

syn match NERDTreeTxtFile #^\s\+.*txt$#
highlight NERDTreeTxtFile ctermbg=red ctermfg=magenta

" Enable autocompletion
let g:neocomplete#enable_at_startup = 1

