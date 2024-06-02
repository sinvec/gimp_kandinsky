from pathlib import Path
import shutil

# копирует файлы из папки client в папку с плагинами GIMP
if __name__ == "__main__":
	home_dir = str(Path.home())
	gimp_plugins_dir = f'{home_dir}\\AppData\\Roaming\\GIMP\\2.10\\plug-ins'
	current_directory = str(Path.cwd())

	code = '\\Kandinsky.py'
	icon = '\\KandinskyIcon.png'

	shutil.copyfile(f'{current_directory}\\client{code}', f'{gimp_plugins_dir}{code}')
	shutil.copyfile(f'{current_directory}\\client{icon}', f'{gimp_plugins_dir}{icon}')

	print(f'Файлы из client были скопированы в папку {gimp_plugins_dir}')