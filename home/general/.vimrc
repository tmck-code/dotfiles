" taken from github.com/tmck-code/dotfiles
" Package manager
execute pathogen#infect()
" Global variables to enable plugins
filetype plugin indent on
filetype plugin on

" Basic editor behaviour
set number    " line numbers
set expandtab " tabs -> spaces
set tabstop=2 " default 2 spaces for indentation
set nowrap    " disable line wrapping by default
syntax on     " basic syntax highlighting
syntax enable " syntax recognition

set textwidth=80     " Set the text width used by `gq` as 100
set formatoptions-=t " Disable auto-wrap at the textwidth:
:set colorcolumn=81  " Sets a visual column marking the width

" mouse behaviour
set mouse=a     " enable mouse
if !has('nvim') " set better click/drag etc, only for neovim
  set ttymouse=xterm2
endif

" autocompletions via built in engine
set omnifunc=syntaxcomplete#Complete " enable built-in engine
" Just select autocomplete option with return, don't also insert a newline
inoremap <expr> <CR> pumvisible() ? "\<C-y>" : "\<C-g>u\<CR>"
" Some better menu defaults
set completeopt+=longest,menuone,noinsert

" Detect file encoding and use utf8 if possible
if has("multi_byte")
  if &termencoding == ""
    let &termencoding = &encoding
    endif
  set encoding=utf-8
  setglobal fileencoding=utf-8
  setglobal bomb
  set fileencodings=ucs-bom,utf-8,latin1
endif

" OSX specific settings -----------------------------------

" yank and paste with OSX clipboard
if has("clipboard")
  set clipboard=unnamed " copy to the system clipboard

  if has("unnamedplus") " X11 support
    set clipboard+=unnamedplus
  endif
endif

" WSL yank support
let s:clip = '/mnt/c/Windows/System32/clip.exe'  " change this path according to your mount point
if executable(s:clip)
    augroup WSLYank
        autocmd!
        autocmd TextYankPost * if v:event.operator ==# 'y' | call system(s:clip, @0) | endif
    augroup END
endif

" set vim as default editor for crontab files
if $VIM_CRONTAB == "true"
    set nobackup
    set nowritebackup
endif

" Language-specific settings --------------------

" Default indentations by file extension
autocmd FileType go  setlocal autoindent noexpandtab tabstop=4 shiftwidth=4
autocmd FileType py  setlocal autoindent expandtab   tabstop=4 shiftwidth=4 textwidth=100 colorcolumn=101
autocmd FileType rb  setlocal autoindent expandtab   tabstop=2 shiftwidth=2
autocmd FileType sh  setlocal autoindent expandtab   tabstop=2 shiftwidth=2
autocmd FileType psv setlocal csv_delim='|'
" autocmd FileType ruby,eruby let g:rubycomplete_buffer_loading = 1
" autocmd FileType ruby,eruby let g:rubycomplete_classes_in_global = 1
" autocmd FileType ruby,eruby let g:rubycomplete_rails = 1

" Python settings
let g:pymode_python = 'python3'
let g:python_highlight_all = 1

" Go settings
" let g:go_fmt_autosave = 1

syn region pythonInterpolation contained matchgroup=pythonQuotes start=/{/ end=/}/ extend contains=ALLBUT,pythonDecoratorName,pythonDecorator,pythonFunction,pythonDoctestValue,pythonDoctest
syn region pythonfString matchgroup=pythonQuotes start=+[fF]\z(['"]\)+ end="\z1" skip="\\\\\|\\\z1" contains=@Spell,pythonInterpolation
syn keyword Keyword self

hi pythonInterpolation ctermfg=12
hi def link pythonfString String

syn region pythonArguments
      \ matchgroup=NONE
      \ start=/\%(\(\<def\>.*\|\<class\>\)\s\+\w\+\)\@<=(/rs=e-2
      \ end=/):/
      \ keepend
      \ contains=pythonString,pythonBuiltin,pythonArgument

syn match pythonArgument /\w\+\([,)=]\)\@=/ contained
hi pythonArgument ctermfg=5

" CSV/PSV settings
let g:csv_delim_test = ',	|'

" Shorctuts & key bindings -----------------------

" Move across panes with Cntrl+Shift+<arrow key>
map <C-S-left>  <C-W><left>
map <C-S-right> <C-W><right>
map <C-S-up>    <C-W><up>
map <C-S-down>  <C-W><down>

" Map Cntrl+N to toggle NERDTree on & off
map <C-N> :NERDTreeFocus<CR>
map ;; :NERDTreeToggle<CR>

" Map Cntrl+S to :w
vmap <C-s> :w<CR>

" Map tab to be autocomplete (Cntrl+N)
if has("gui_running")
    " C-Space seems to work under gVim on both Linux and win32
    inoremap <C-Space> <C-n>
else
  if has("unix")
    inoremap <Nul> <C-n>
  endif
endif

" Colours ----------------------------------------

" let g:airline_theme='shades_of_purple'
" let g:shades_of_purple_airline = 1
let g:airline_powerline_fonts = 1

if ($TERMUX_THEME == "light")
  set background=light " Light style for theme
else
  set background=dark " Dark style for theme
endif

" colorscheme horizon " Set current theme
colorscheme gruvbox
" Set comments to appear in italics for all colorschemes
highlight Comment cterm=italic

" ensure colours work correctly even in tmux
if &term =~ '256color'
" disable Background Color Erase (BCE) so that color schemes
" render properly when inside 256-color tmux and GNU screen.
" see also http://snk.tuxfamily.org/log/vim-256color-bce.html
  set t_ut=
  " Activate 256 colors
  set t_Co=256
  " If terminal supports truecolor, this is needed for correct colours
  " - via https://github.com/crusoexia/vim-monokai#terminal-support
  if has("termguicolors")
    set termguicolors
  endif
endif

" Fix italics in Vim
if !has('nvim')
  let &t_ZH="\e[3m"
  let &t_ZR="\e[23m"
endif
let &t_ZH="\e[3m"
let &t_ZR="\e[23m"
highlight Comment cterm=italic


" Plugin settings -------------------------------

" if has('nvim') " set better click/drag etc, only for neovim
"   let g:deoplete#enable_at_startup = 1
" endif

let g:jedi#auto_initialization = 0
" Syntastic Python version
let g:syntastic_python_python_exec = 'python3'
let g:syntastic_python_checkers = ['pylint']
let g:syntastic_check_on_open = 0
let g:syntastic_check_on_wq = 1

" Terraform settings
let g:terraform_align=1
let g:terraform_fold_sections=1

" EasyAlign
" Start interactive EasyAlign in visual mode (e.g. vipga)
xmap ga <Plug>(EasyAlign)
" Start interactive EasyAlign for a motion/text object (e.g. gaip)
nmap ga <Plug>(EasyAlign)

" FZF (FuZzy Finder)
set rtp+=~/.fzf

" let b:RainbowDelim = '|'
" Rainbow parenthesis
let g:rbpt_colorpairs = [
    \ ['brown',       'RoyalBlue3'],
    \ ['Darkblue',    'SeaGreen3'],
    \ ['darkgray',    'DarkOrchid3'],
    \ ['darkgreen',   'firebrick3'],
    \ ['darkcyan',    'RoyalBlue3'],
    \ ['darkred',     'SeaGreen3'],
    \ ['darkmagenta', 'DarkOrchid3'],
    \ ['brown',       'firebrick3'],
    \ ['gray',        'RoyalBlue3'],
    \ ['black',       'SeaGreen3'],
    \ ['darkmagenta', 'DarkOrchid3'],
    \ ['Darkblue',    'firebrick3'],
    \ ['darkgreen',   'RoyalBlue3'],
    \ ['darkcyan',    'SeaGreen3'],
    \ ['darkred',     'DarkOrchid3'],
    \ ['red',         'firebrick3'],
    \ ]

let g:rbpt_max = 16 " let g:rbpt_loadcmd_toggle = 0

" better-whitespace settings
let g:better_whitespace_enabled=1 " Enable syntax highlighting for trailing whitespace
let g:strip_whitespace_on_save=1  " Strip whitespace on save
let g:strip_whitespace_confirm=0  " Strip whitespace without asking for confirmation

" ctrlp settings
" speed up because it's slow af
let g:ctrlp_cache_dir = $HOME . '/.cache/ctrlp'
if executable('ag')
  let g:ctrlp_user_command = 'ag %s -l --nocolor -g ""'
endif
let g:ctrlp_user_command = ['.git/', 'git --git-dir=%s/.git ls-files -oc --exclude-standard']
" Open files in a new tab when selecting (pressing enter or clicking)
let g:ctrlp_prompt_mappings = {
    \ 'AcceptSelection("e")': ['<2-LeftMouse>'],
    \ 'AcceptSelection("t")': ['<cr>'],
    \ }

" Silicon png code generator
let g:silicon = {
      \ 'theme':                 '1337',
      \ 'font':                  'Hack',
      \ 'background':         '#aaaaff',
      \ 'shadow-color':       '#555555',
      \ 'line-pad':                   2,
      \ 'pad-horiz':                 80,
      \ 'pad-vert':                 100,
      \ 'shadow-blur-radius':         0,
      \ 'shadow-offset-x':            0,
      \ 'shadow-offset-y':            0,
      \ 'line-number':           v:true,
      \ 'round-corner':          v:true,
      \ 'window-controls':       v:true,
      \ }
" Terraform settings
let g:terraform_align=1
let g:terraform_fold_sections=1
let g:terraform_remap_spacebar=1

" NERDTree settings
" open NERDTree by default
autocmd vimenter * if !argc() | NERDTree | endif
autocmd bufenter * if (winnr("$") == 1 && exists("b:NERDTreeType") && b:NERDTreeType == "primary") | q | endif
syn match NERDTreeTxtFile #^\s\+.*txt$#
let g:NERDTreeLimitedSyntax = 1 " Only enable NerdTree syntax highlighting on common file types
" Set some colours
highlight NERDTreeTxtFile ctermbg=red ctermfg=magenta

" vim-better-whitespace settings -----------------
let g:better_whitespace_enabled=1
let g:strip_whitespace_on_save=1

" airline settings -------------------------------
" Disable editor mode in default bar (as this is displayed by airline)
set noshowmode

let g:webdevicons_enable_airline_statusline = 1
let g:webdevicons_enable_airline_tabline = 1

" Searching options
let g:ctrlsf_position = 'bottom'
let g:ctrlsf_winsize = '30%'
let g:ctrlsf_backend = 'ag'
let g:go_bin_path = $HOME."/go/bin"

