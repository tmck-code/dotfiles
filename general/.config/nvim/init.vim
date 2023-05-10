" github.com/tmck-code/dotfiles

" set runtimepath^=~/.vim runtimepath+=~/.vim/after
set runtimepath^=~/.vim runtimepath+=~/.config/nvim
let &packpath = &runtimepath

execute pathogen#infect()

" Basic editor behaviour -------------------------

set number

" Shorctuts & key bindings -----------------------

" move across panes with Cntrl+Shift+<arrow key>
map <C-S-left>  <C-W><left>
map <C-S-right> <C-W><right>
map <C-S-up>    <C-W><up>
map <C-S-down>  <C-W><down>

" map Cntrl+N to toggle file tree on & off
map <C-N> :CHADopen<CR>
map ;; :CHADopen<CR>

" map Cntrl+S to :w
vmap <C-s> :w<CR>

" Colours ----------------------------------------

set termguicolors
highlight Comment cterm=italic
" colorscheme
colorscheme aurora
set background=dark

" enable sexy status line
let g:airline_powerline_fonts = 1

" Set comments to appear in italics for all colorschemes
highlight Comment cterm=italic gui=italic

" Plugin settings -------------------------------

" vim-better-whitespace settings -----------------
let g:better_whitespace_enabled=1
let g:strip_whitespace_on_save=1
