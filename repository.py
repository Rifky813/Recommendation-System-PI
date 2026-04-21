import requests
from bs4 import BeautifulSoup

url = 'https://library.gunadarma.ac.id/repository?jenis=&fakultas=&judul=vclass&keyword=&nomoranggota=&penulis=&nomorinduk=&pembimbing='
request = requests.get(url)
request.raise_for_status()
print(f'{request.status_code} = {request.reason}')

html = request.text
soup = BeautifulSoup(html, 'html.parser')

list_judul = soup.find_all('div', class_='card shadow')

nama_judul = []
jurusan = []

for judul in list_judul:
    nama_judul.append(judul.find('h5', class_='card-title font-weight-bold text-purple').text.strip())
    jurusan.append(judul.find('h6', class_='card-subtitle').text.split('|')[2].strip())

print('\n'.join(nama_judul))
print('\n'.join(jurusan))