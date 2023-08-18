cls
$file = ".\script.txt"
$data = Get-Content $file -Encoding byte
$compressed = New-Object IO.MemoryStream
$gzip = New-Object System.IO.Compression.GZipStream $compressed, ([Io.Compression.CompressionMode]"Compress")
$gzip.Write($data, 0, $data.Length)
$gzip.Close()
$encoded = [System.BitConverter]::ToString($compressed.ToArray()).Split('-')
$key = [System.Enum]::GetValues([System.ConsoleColor])
Write-Host ""
Write-Host ""

$wrap = 400		# How many characters per line
$batch = 60		# How many lines per batch (for easier screenshot cropping)

$batch_lines = 1
for($i = 0; $i -lt $encoded.Length; $i++){
	$f = $key[[Int32]("0x"+$encoded[$i][0])]
	$b = $key[[Int32]("0x"+$encoded[$i][1])]
	Write-Host -NoNewline -ForegroundColor $f -BackgroundColor $b "$([char]0x0258C)"
	if(($i+1) % 200 -Eq 0){
		Write-Host ""
		$batch_lines += 1
	}

	if ($batch_lines -gt 60) {
		Write-Host ""
		$batch_lines = 1
	}
}
Write-Host ""
Write-Host ""
