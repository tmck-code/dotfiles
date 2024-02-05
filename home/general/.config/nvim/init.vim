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
" map <C-N> :CHADopen<CR>
" map ;; :CHADopen<CR>

" if v:vim_did_enter
"   call CHADopen
" else
"   au VimEnter * CHADopen
" endif

" Colours ----------------------------------------

" make comments italic
highlight Comment cterm=italic gui=italic

" TrueColor config
" For Neovim 0.1.3 and 0.1.4 - https://github.com/neovim/neovim/pull/2198
if (has('nvim'))
  let $NVIM_TUI_ENABLE_TRUE_COLOR = 1
endif
" For Neovim > 0.1.5 and Vim > patch 7.4.1799 - https://github.com/vim/vim/commit/61be73bb0f965a895bfb064ea3e55476ac175162
" Based on Vim patch 7.4.1770 (`guicolors` option) - https://github.com/vim/vim/commit/8a633e3427b47286869aa4b96f2bfc1fe65b25cd
" https://github.com/neovim/neovim/wiki/Following-HEAD#20160511
if (has('termguicolors'))
  set termguicolors
endif

" colorscheme aurora
set background=dark
let g:material_terminal_italics = 1
let g:material_theme_style = 'darker-community'
colorscheme material

let g:airline_theme = 'material'

let g:airline_powerline_fonts = 1
let g:markdown_fenced_languages = ['html', 'python', 'lua', 'vim', 'typescript', 'javascript', 'json']

