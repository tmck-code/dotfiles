" package manager
execute pathogen#infect()

" global variables to enable plugins
syntax on
filetype plugin indent on
syntax enable
set clipboard=unnamed
set mouse=a
set ttymouse=xterm2

" very basic editor behaviour
set number    " line numbers
set expandtab " tabs -> spaces
set tabstop=2 " ruby-level indentation
set nowrap    " no line wrapping (for my 13" screen)

" Shorctuts & key bindings --------------------------------

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

vmap <C-s> :w<CR>

" Terraform
let g:terraform_align=1
let g:terraform_fold_sections=1
let g:terraform_remap_spacebar=1

" Colours ------------------------------------------------
if has("termguicolors")
    set termguicolors
endif

set background=dark
set t_Co=256

let g:quantum_italics = 1
colorscheme onedark

" Syntastic

set statusline+=%#warningmsg#
set statusline+=%{SyntasticStatuslineFlag()}
set statusline+=%*

let g:syntastic_always_populate_loc_list = 1
let g:syntastic_auto_loc_list = 1
let g:syntastic_check_on_wq = 1

" highlight errors
let g:syntastic_enable_highlighting=1
let g:syntastic_enable_signs=1

let g:syntastic_python_checkers = ['pylint']

" NERDTree settings ---------------------------------------

" Set a bigger width
let g:NERDTreeWinSize=40

" open NERDTree by default
autocmd vimenter * if !argc() | NERDTree | endif
autocmd bufenter * if (winnr("$") == 1 && exists("b:NERDTreeType") && b:NERDTreeType == "primary") | q | endif

syn match NERDTreeTxtFile #^\s\+.*txt$#
highlight NERDTreeTxtFile ctermbg=red ctermfg=magenta

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
" These can be commented out in favour of non-nerd statusline symbols
let g:airline_theme='one'
let g:airline_powerline_fonts = 1
let g:webdevicons_enable_airline_statusline = 1
let g:webdevicons_enable_airline_tabline = 1
let g:WebDevIconsNerdTreeAfterGlyphPadding = '  '

" Enable autocompletion
let g:neocomplete#enable_at_startup = 1

" Language-specific formatting
autocmd FileType go setlocal autoindent noexpandtab tabstop=4 shiftwidth=4
autocmd FileType py setlocal autoindent expandtab tabstop=4 shiftwidth=4
autocmd FileType rb setlocal autoindent expandtab tabstop=2 shiftwidth=2
autocmd FileType sh setlocal autoindent expandtab tabstop=2 shiftwidth=2

" OSX specific --------------------------------------------

" edit crontab files
if $VIM_CRONTAB == "true"
    set nobackup
    set nowritebackup
endif


