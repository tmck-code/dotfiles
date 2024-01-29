set runtimepath^=~/.nvim
let &packpath = &runtimepath

execute pathogen#infect()
source ~/.vimrc

" Shorctuts & key bindings -----------------------

" move across panes with Cntrl+Shift+<arrow key>
map <C-S-left>  <C-W><left>
map <C-S-right> <C-W><right>
map <C-S-up>    <C-W><up>
map <C-S-down>  <C-W><down>

" map Cntrl+N to toggle NERDTree on & off
map <C-N> :CHADopen<CR>
map ;; :CHADopen<CR>

" Colours ----------------------------------------
set termguicolors
colorscheme aurora
set background=dark

" make comments italic
highlight Comment cterm=italic gui=italic

let g:airline_powerline_fonts = 1

" enter chadtree _after_ setting colours
if v:vim_did_enter
  call CHADopen
else
  au VimEnter * CHADopen
endif

