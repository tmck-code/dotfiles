set runtimepath^=~/.vim runtimepath+=~/.vim/after
let &packpath = &runtimepath
source ~/.vimrc

execute pathogen#infect()

" PATHs and such ---------------------------------
" set python3 path
let g:python3_host_prog="/home/freman/.venv/bin/python3"
" disable perl
let g:loaded_perl_provider = 0

" Shorctuts & key bindings -----------------------

" move across panes with Cntrl+Shift+<arrow key>
map <C-S-left>  <C-W><left>
map <C-S-right> <C-W><right>
map <C-S-up>    <C-W><up>
map <C-S-down>  <C-W><down>

" Colours ----------------------------------------

" TrueColor config
" from https://github.com/neovim/neovim/pull/2198
if (has('nvim'))
  let $NVIM_TUI_ENABLE_TRUE_COLOR = 1
endif

" from https://github.com/neovim/neovim/wiki/Following-HEAD#20160511
if (has('termguicolors'))
  set termguicolors
endif

set background=dark
let g:material_terminal_italics = 1
let g:material_style = 'deep ocean'
colorscheme material

let g:airline_theme = 'google_dark'

let g:airline_powerline_fonts = 1
let g:markdown_fenced_languages = ['html', 'python', 'lua', 'vim', 'typescript', 'javascript', 'json']

" make comments italic (note: this must be set AFTER the colorscheme)
highlight Comment cterm=italic gui=italic
