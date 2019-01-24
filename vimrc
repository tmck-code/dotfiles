" package manager
execute pathogen#infect()

" global variables to enable plugins
syntax on
filetype plugin indent on
syntax enable

" yank to clipboard
if has("clipboard")
  set clipboard=unnamed " copy to the system clipboard

  if has("unnamedplus") " X11 support
    set clipboard+=unnamedplus
  endif
endif

set mouse=a
set ttymouse=xterm2

" very basic editor behaviour
set number    " line numbers
set expandtab " tabs -> spaces
set tabstop=2 " default to 2 spaces for indentation
set nowrap    " no line wrapping by default

if &term =~ '256color'
    " disable Background Color Erase (BCE) so that color schemes
    " render properly when inside 256-color tmux and GNU screen.
    " see also http://snk.tuxfamily.org/log/vim-256color-bce.html
    set t_ut=
endif

set background=dark
set t_Co=256

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

" Language-specific settings
autocmd FileType go setlocal autoindent noexpandtab tabstop=4 shiftwidth=4
autocmd FileType py setlocal autoindent expandtab   tabstop=4 shiftwidth=4
autocmd FileType rb setlocal autoindent expandtab   tabstop=2 shiftwidth=2
autocmd FileType sh setlocal autoindent expandtab   tabstop=2 shiftwidth=2

" Python settings
let g:pymode_python = 'python3'

" (OSX specific) edit crontab files
if $VIM_CRONTAB == "true"
    set nobackup
    set nowritebackup
endif

" Enable syntax highlighting for trailing whitespace
let g:better_whitespace_enabled=1
" Strip whitespace on save
let g:strip_whitespace_on_save=1

" Shorctuts & key bindings -----------------------

" Move across panes with Cntrl+Shift+<arrow key>
map <C-S-left> <C-W><left>
map <C-S-right> <C-W><right>
map <C-S-up> <C-W><up>
map <C-S-down> <C-W><down>

" Resize panes
map <C-D-left> <C-W><<>
map <C-D-right> :vertical resize -20<CR>

" Map Cntrl+N to toggle NERDTree on & off
map <C-N> :NERDTreeFocus<CR>
map <C-n> :NERDTreeToggle<CR>

" Map Cntrl+S to :w
vmap <C-s> :w<CR>

" Colours ----------------------------------------

" set background=dark
set t_Co=256

let g:quantum_italics = 1
colorscheme one

if has("termguicolors")
    set termguicolors
endif

" Map tab to be autocomplete (Cntrl+N)
if has("gui_running")
    " C-Space seems to work under gVim on both Linux and win32
    inoremap <C-Space> <C-n>
else
  if has("unix")
    inoremap <Nul> <C-n>
  endif
endif

" Terraform settings -----------------------------

let g:terraform_align=1
let g:terraform_fold_sections=1
let g:terraform_remap_spacebar=1

" NERDTree settings ------------------------------

" open NERDTree by default
autocmd vimenter * if !argc() | NERDTree | endif
autocmd bufenter * if (winnr("$") == 1 && exists("b:NERDTreeType") && b:NERDTreeType == "primary") | q | endif

syn match NERDTreeTxtFile #^\s\+.*txt$#
" Set some colours
highlight NERDTreeTxtFile ctermbg=red ctermfg=magenta

" vim-better-whitespace settings -----------------
let g:better_whitespace_enabled=1
let g:strip_whitespace_on_save=1

" airline settings -------------------------------

" Disable editor mode in default bar (as this is displayed by airline)
set noshowmode

" Only enable NerdTree syntax highlighting on common file types
let g:NERDTreeLimitedSyntax = 1

" Status bar and devicon settings
" These can be commented out in favour of non-nerd statusline symbols
let g:airline_theme='one'
" let g:airline_powerline_fonts = 1
let g:webdevicons_enable_airline_statusline = 1
let g:webdevicons_enable_airline_tabline = 1

" Searching options
let g:ctrlsf_position = 'bottom'
let g:ctrlsf_winsize = '30%'

" Language-specific formatting
autocmd FileType go setlocal autoindent noexpandtab tabstop=4 shiftwidth=4
autocmd FileType py setlocal autoindent expandtab tabstop=4 shiftwidth=4
autocmd FileType rb setlocal autoindent expandtab tabstop=2 shiftwidth=2
autocmd FileType sh setlocal autoindent expandtab tabstop=2 shiftwidth=2

" Alignment

" Start interactive EasyAlign in visual mode (e.g. vipga)
xmap ga <Plug>(EasyAlign)

" Start interactive EasyAlign for a motion/text object (e.g. gaip)
nmap ga <Plug>(EasyAlign)

" OSX specific --------------------------------------------

" edit crontab files
if $VIM_CRONTAB == "true"
    set nobackup
    set nowritebackup
endif

